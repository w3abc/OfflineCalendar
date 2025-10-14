import sys
import re
import json
import os
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QGridLayout, QPushButton, QComboBox, QFrame, QDialog, QTextEdit,
    QSpinBox, QMessageBox, QDialogButtonBox, QSystemTrayIcon, QMenu
)
from lunar_python import Solar, SolarMonth, Lunar
from lunar_python.util import HolidayUtil, LunarUtil, SolarUtil

class DayCell(QFrame):
    """Custom widget for a single day in the calendar grid."""
    day_clicked = Signal(Solar)

    def __init__(self, solar_day=None):
        super().__init__()
        self.solar_day = solar_day
        self.setProperty("is_selected", False)

        self.setFrameShape(QFrame.NoFrame)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.layout().setSpacing(0)

        self.solar_label = QLabel()
        self.major_festival_label = QLabel()
        self.lunar_label = QLabel()
        self.holiday_label = QLabel(self)

        self.solar_label.setAlignment(Qt.AlignCenter)
        self.major_festival_label.setAlignment(Qt.AlignCenter)
        self.lunar_label.setAlignment(Qt.AlignCenter)

        self.solar_label.setObjectName("solar_label")
        self.major_festival_label.setObjectName("major_festival_label")
        self.lunar_label.setObjectName("lunar_label")
        self.holiday_label.setObjectName("holiday_label")

        self.layout().addWidget(self.solar_label)
        self.layout().addWidget(self.major_festival_label)
        self.layout().addWidget(self.lunar_label)

        if self.solar_day:
            self.set_day()

    def set_day(self):
        lunar_day = self.solar_day.getLunar()
        self.solar_label.setText(str(self.solar_day.getDay()))

        major_lunar_festivals = lunar_day.getFestivals()
        major_solar_festivals = self.solar_day.getFestivals()
        all_major_festivals = major_lunar_festivals + major_solar_festivals
        self.major_festival_label.setText(all_major_festivals[0] if all_major_festivals else "")

        lunar_text = f"{lunar_day.getMonthInChinese()}月{lunar_day.getDayInChinese()}"
        self.lunar_label.setText(lunar_day.getJieQi() or lunar_text)

        is_weekend = self.solar_day.getWeek() == 0 or self.solar_day.getWeek() == 6
        holiday = HolidayUtil.getHoliday(self.solar_day.getYear(), self.solar_day.getMonth(), self.solar_day.getDay())
        
        self.setProperty("is_rest", False)
        self.setProperty("is_work", False)
        self.setProperty("is_today", self.solar_day.toYmd() == datetime.now().strftime("%Y-%m-%d"))

        self.holiday_label.setText("")
        if holiday:
            if holiday.isWork():
                self.holiday_label.setText("班")
                self.setProperty("is_work", True)
            else:
                self.holiday_label.setText("休")
                self.setProperty("is_rest", True)
        elif is_weekend:
            self.holiday_label.setText("休")
            self.setProperty("is_rest", True)
        
        # Position the holiday_label
        self.holiday_label.move(5, 5) # Move to top-left with some padding
        self.holiday_label.adjustSize() # Adjust size to fit content

    def mousePressEvent(self, event):
        if self.solar_day:
            self.day_clicked.emit(self.solar_day)
        super().mousePressEvent(event)

    def set_selected(self, selected):
        self.setProperty("is_selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

class MainWindow(QMainWindow):
    def _get_user_holidays_path(self):
        config_dir = os.path.expanduser("~/.config/OfflineCalendar")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "user_holidays.json")

    def load_user_holidays(self):
        holidays_file = self._get_user_holidays_path()
        try:
            with open(holidays_file, "r") as f:
                user_data = json.load(f)
                if isinstance(user_data, dict):
                    for year, data_string in user_data.items():
                        HolidayUtil.fix(None, data_string)
        except (FileNotFoundError, json.JSONDecodeError):
            pass # File doesn't exist or is invalid, just ignore

    def __init__(self):
        super().__init__()
        self.load_user_holidays()

        self.setWindowTitle("万年历本地版")
        self.setObjectName("WanNianLiBenDiBan")
        self.setGeometry(100, 100, 1100, 700)

        # 设置应用程序图标
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.selected_cell = None
        self.app = QApplication.instance()
        self.holiday_dates = {}

        # 系统托盘相关
        self.settings = QSettings("OfflineCalendar", "WanNianLi")
        self.tray_icon = None

        # 初始化系统托盘
        self.setup_system_tray()

        # --- Date State ---
        today = datetime.now()
        self.year = today.year
        self.month = today.month
        self.day = today.day

        # --- UI Initialization ---
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(main_widget)

        self.setup_left_panel()
        right_panel = self.setup_right_panel()

        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(right_panel)

        # --- Connect Signals ---
        self.year_combo.currentIndexChanged.connect(self.on_date_change)
        self.month_combo.currentIndexChanged.connect(self.on_date_change)
        self.holiday_combo.currentIndexChanged.connect(self.on_holiday_selected)
        self.import_button.clicked.connect(self.on_import_holidays_clicked)
        self.today_button.clicked.connect(self.go_to_today)

        # --- Initial Draw & Style ---
        self.setup_styles()
        self.update_combo_boxes()
        self.update_holiday_combo()
        self.draw_calendar()

    def parse_holiday_text(self, year, text):
        from datetime import timedelta
        from lunar_python import Lunar

        data_string = ""
        name_to_index = {name: i for i, name in enumerate(HolidayUtil.NAMES)}

        holiday_configs = {
            "元旦节": {
                "pattern": r"元旦：(\d+)月(\d+)日.*?放假",
                "groups": ["m", "d"],
            },
            "春节": {
                "pattern": r"春节：(\d+)月(\d+)日.*?至(\d+)月(\d+)日.*?放假.*?((?:.|\n)+?上班)",
                "groups": ["sm", "sd", "em", "ed", "work"],
            },
            "清明节": {
                "pattern": r"清明节：(\d+)月(\d+)日.*?至\s*(\d+)日.*?放假",
                "groups": ["sm", "sd", "ed"],
            },
            "劳动节": {
                "pattern": r"劳动节：(\d+)月(\d+)日.*?至\s*(\d+)日.*?放假.*?((?:.|\n)+?上班)",
                "groups": ["sm", "sd", "ed", "work"],
            },
            "端午节": {
                "pattern": r"端午节：(\d+)月(\d+)日.*?至(\d+)月(\d+)日.*?放假",
                "groups": ["sm", "sd", "em", "ed"],
            },
            "国庆中秋": {
                "pattern": r"国庆节、中秋节：(\d+)月(\d+)日.*?至\s*(\d+)日.*?放假.*?((?:.|\n)+?上班)",
                "groups": ["sm", "sd", "ed", "work"],
            }
        }

        for holiday_name, config in holiday_configs.items():
            match = re.search(config["pattern"], text, re.DOTALL)
            if not match:
                continue

            parts = {name: val for name, val in zip(config["groups"], match.groups())}
            
            vacation_days = []
            work_days = []

            try:
                sm = int(parts.get("sm", parts.get("m")))
                sd = int(parts.get("sd", parts.get("d")))
                em = int(parts.get("em", sm))
                ed = int(parts.get("ed", sd))

                start_date = datetime(year, sm, sd)
                end_date = datetime(year, em, ed)
                current_date = start_date
                while current_date <= end_date:
                    vacation_days.append(current_date)
                    current_date += timedelta(days=1)
            except (ValueError, TypeError):
                continue

            if "work" in parts:
                work_days_text = parts.get("work", "")
                work_day_matches = re.findall(r"(\d+)月(\d+)日", work_days_text)
                for wm, wd in work_day_matches:
                    work_days.append(datetime(year, int(wm), int(wd)))

            name_index = name_to_index.get(holiday_name)
            if name_index is None:
                continue

            # Use the first day of the vacation as the target date for simplicity and consistency
            target_date_str = vacation_days[0].strftime("%Y%m%d")

            for day in vacation_days:
                day_str = day.strftime("%Y%m%d")
                data_string += f"{day_str}{name_index}1{target_date_str}"
            
            for day in work_days:
                day_str = day.strftime("%Y%m%d")
                data_string += f"{day_str}{name_index}0{target_date_str}"

        return data_string

    def on_import_holidays_clicked(self):
        dialog = ImportDialog(self, self.year)
        if dialog.exec():
            year, text = dialog.get_data()
            if not text.strip():
                QMessageBox.warning(self, "警告", "输入的文本不能为空。")
                return
            
            try:
                data_str = self.parse_holiday_text(year, text)
                if not data_str:
                    QMessageBox.warning(self, "失败", "未能从文本中解析出有效的假期数据。")
                    return

                holidays_file = self._get_user_holidays_path()
                user_data = {}
                try:
                    with open(holidays_file, "r") as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, dict):
                            user_data = existing_data
                except (FileNotFoundError, json.JSONDecodeError):
                    pass

                user_data[str(year)] = data_str

                with open(holidays_file, "w") as f:
                    json.dump(user_data, f, ensure_ascii=False, indent=4)

                # Apply the new data to the current session and refresh
                HolidayUtil.fix(None, data_str)
                self.update_holiday_combo()
                self.draw_calendar()

                QMessageBox.information(self, "成功", f"成功为 {year} 年导入并保存了假期数据。\n\n文件已保存至：{os.path.abspath(holidays_file)}")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"解析或保存数据时发生错误：\n{e}")




    def setup_left_panel(self):
        self.left_panel = QWidget()
        self.left_panel.setFixedWidth(350)
        self.left_panel.setObjectName("left_panel")
        layout = QVBoxLayout(self.left_panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignTop)

        # --- Create Labels ---
        self.details_year_month_label = QLabel()
        self.details_day_display = QLabel()
        self.details_lunar_weekday_label = QLabel()
        self.details_ganzhi_label = QLabel()
        self.details_festivals_label = QLabel()
        self.details_yi_label = QLabel()
        self.details_ji_label = QLabel()

        # --- Set Object Names for Styling ---
        self.details_year_month_label.setObjectName("details_year_month_label")
        self.details_day_display.setObjectName("details_day_display")
        self.details_lunar_weekday_label.setObjectName("details_lunar_weekday_label")
        self.details_ganzhi_label.setObjectName("details_ganzhi_label")
        self.details_festivals_label.setObjectName("details_festivals_label")
        self.details_yi_label.setObjectName("details_yi_label")
        self.details_ji_label.setObjectName("details_ji_label")

        # --- Configure Label Properties ---
        self.details_festivals_label.setWordWrap(True)
        self.details_yi_label.setWordWrap(True)
        self.details_ji_label.setWordWrap(True)
        
        for label in [self.details_year_month_label, self.details_day_display, self.details_lunar_weekday_label, self.details_ganzhi_label, self.details_festivals_label]:
            label.setAlignment(Qt.AlignCenter)

        # --- Layout ---
        layout.addWidget(self.details_year_month_label)
        layout.addSpacing(5)
        layout.addWidget(self.details_day_display)
        layout.addSpacing(5)
        layout.addWidget(self.details_lunar_weekday_label)
        layout.addSpacing(10)
        layout.addWidget(self.details_ganzhi_label)
        layout.addSpacing(15)
        layout.addWidget(self.details_festivals_label)
        layout.addSpacing(25)

        # Yi/Ji Section
        yi_ji_layout = QGridLayout()
        yi_ji_layout.setColumnStretch(1, 1)
        
        yi_icon = QLabel("宜")
        ji_icon = QLabel("忌")
        yi_icon.setObjectName("yi_icon")
        ji_icon.setObjectName("ji_icon")
        yi_icon.setAlignment(Qt.AlignCenter)
        ji_icon.setAlignment(Qt.AlignCenter)

        yi_ji_layout.addWidget(yi_icon, 0, 0)
        yi_ji_layout.addWidget(self.details_yi_label, 0, 1)
        yi_ji_layout.setRowMinimumHeight(0, 30)
        
        yi_ji_layout.addWidget(ji_icon, 1, 0)
        yi_ji_layout.addWidget(self.details_ji_label, 1, 1)
        yi_ji_layout.setRowMinimumHeight(1, 30)

        yi_ji_layout.setSpacing(15)
        layout.addLayout(yi_ji_layout)

        layout.addStretch()

    def setup_right_panel(self):
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        controls_layout = QHBoxLayout()
        self.year_combo = QComboBox()
        self.year_combo.addItems([str(y) for y in range(1901, 2101)])
        self.month_combo = QComboBox()
        self.month_combo.addItems([str(m) for m in range(1, 13)])
        self.holiday_combo = QComboBox()
        self.import_button = QPushButton("导入假期")
        self.today_button = QPushButton("今天")

        controls_layout.addWidget(self.year_combo)
        controls_layout.addWidget(QLabel("年"))
        controls_layout.addWidget(self.month_combo)
        controls_layout.addWidget(QLabel("月"))
        controls_layout.addSpacing(20)
        controls_layout.addWidget(self.holiday_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.import_button)
        controls_layout.addWidget(self.today_button)

        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(0)
        days_of_week = ["日", "一", "二", "三", "四", "五", "六"]
        for i, day in enumerate(days_of_week):
            header = QLabel(day)
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("padding: 10px; font-weight: bold;")
            if i == 0 or i == 6:
                header.setStyleSheet("padding: 10px; font-weight: bold; color: #e13844;")
            self.calendar_grid.addWidget(header, 0, i)

        right_layout.addLayout(controls_layout)
        right_layout.addLayout(self.calendar_grid)
        return right_panel

    def setup_styles(self):
        qss = """
            QMainWindow { background-color: #f8f9fa; }
            #left_panel { 
                background-color: #fff; 
                border-right: 1px solid #dee2e6; 
            }

            /* Left Panel Details */
            #details_year_month_label {
                font-size: 18px;
                color: #333;
            }
            #details_day_display { 
                font-size: 90pt; 
                font-weight: 500; 
                color: #333;
                line-height: 1;
            }
            #details_lunar_weekday_label {
                font-size: 16px;
                color: #555;
            }
            #details_ganzhi_label {
                font-size: 13px;
                color: #888;
            }
            #details_festivals_label {
                font-size: 14px;
                color: #555;
                font-weight: bold;
            }
            #yi_icon, #ji_icon {
                font-size: 14px;
                font-weight: bold;
                color: white;
                border-radius: 4px;
                padding: 4px;
                min-width: 22px;
                min-height: 22px;
            }
            #yi_icon { background-color: #3498db; }
            #ji_icon { background-color: #e74c3c; }
            
            #details_yi_label, #details_ji_label {
                font-size: 14px;
                color: #333;
            }

            /* Calendar Grid */
            DayCell {
                background-color: #fff;
                border: 1px solid #f1f1f1;
            }
            DayCell:hover { 
                border: 1px solid #4E6EF2; 
            }
            DayCell[is_selected="true"] {
                background-color: #e0e8ff;
                border: 1px solid #4E6EF2;
            }
            DayCell[is_today="true"] #solar_label {
                background-color: #4E6EF2;
                color: white;
                border-radius: 10px;
            }

            DayCell #solar_label { font-size: 18pt; font-weight: bold; padding: 2px;}
            DayCell #major_festival_label { color: #e13844; font-size: 9pt; font-weight: bold; }
            DayCell #lunar_label { color: #888; font-size: 10pt; }
            DayCell #holiday_label { font-size: 9pt; font-weight: bold; padding: 2px; }

            DayCell[is_rest="true"] #solar_label { color: #e13844; }
            DayCell[is_rest="true"] #holiday_label { color: #28a745; }
            DayCell[is_work="true"] #holiday_label { color: #888; }
        """
        self.app.setStyleSheet(qss)

    def draw_calendar(self):
        for i in reversed(range(self.calendar_grid.count())):
            row, _, _, _ = self.calendar_grid.getItemPosition(i)
            if row > 0:
                item = self.calendar_grid.takeAt(i)
                if item and item.widget():
                    item.widget().deleteLater()

        month_data = SolarMonth.fromYm(self.year, self.month)
        if not month_data: return

        days = month_data.getDays()
        start_col = days[0].getWeek()

        row = 1
        col = start_col
        for day in days:
            cell = DayCell(day)
            cell.day_clicked.connect(self.on_day_selected)
            self.calendar_grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1
        
        self.on_day_selected(Solar.fromYmd(self.year, self.month, self.day))

    def on_day_selected(self, solar_day, cell=None):
        self.year = solar_day.getYear()
        self.month = solar_day.getMonth()
        self.day = solar_day.getDay()

        if self.selected_cell:
            self.selected_cell.set_selected(False)
        
        if not cell:
            for i in range(self.calendar_grid.count()):
                widget = self.calendar_grid.itemAt(i).widget()
                if isinstance(widget, DayCell) and widget.solar_day and widget.solar_day.toYmd() == solar_day.toYmd():
                    cell = widget
                    break
        
        if cell:
            cell.set_selected(True)
            self.selected_cell = cell

        # Update left panel
        lunar_day = solar_day.getLunar()
        
        self.details_year_month_label.setText(f"{solar_day.getYear()}年{solar_day.getMonth()}月")
        self.details_day_display.setText(str(solar_day.getDay()))
        self.details_lunar_weekday_label.setText(f"{lunar_day.getMonthInChinese()}月{lunar_day.getDayInChinese()} 星期{solar_day.getWeekInChinese()}")
        self.details_ganzhi_label.setText(f"{lunar_day.getYearInGanZhi()}年 {lunar_day.getMonthInGanZhi()}月 {lunar_day.getDayInGanZhi()}日 【属{lunar_day.getYearShengXiao()}】")

        festivals = lunar_day.getFestivals() + solar_day.getFestivals() + solar_day.getOtherFestivals()
        festivals = list(dict.fromkeys(festivals))
        self.details_festivals_label.setText(" ".join(festivals) or "")
        
        self.details_yi_label.setText(" ".join(lunar_day.getDayYi()))
        self.details_ji_label.setText(" ".join(lunar_day.getDayJi()))

    def update_holiday_combo(self):
        self.holiday_combo.blockSignals(True)
        self.holiday_combo.clear()
        self.holiday_dates.clear()
        self.holiday_combo.addItem("选择法定节假日", None)

        holidays = HolidayUtil.getHolidays(self.year)
        if holidays:
            for h in holidays:
                # Only add the main holiday day, not the compensated work days
                if not h.isWork() and h.getDay() == h.getTarget():
                    name = h.getName()
                    if name not in self.holiday_dates:
                        date_str = h.getDay()
                        parts = date_str.split('-')
                        year = int(parts[0])
                        month = int(parts[1])
                        day = int(parts[2])
                        self.holiday_dates[name] = Solar.fromYmd(year, month, day)
        
        for name in self.holiday_dates.keys():
            self.holiday_combo.addItem(name)

        self.holiday_combo.blockSignals(False)

    def on_holiday_selected(self, index):
        if index <= 0: # Ignore the placeholder
            return
        
        name = self.holiday_combo.itemText(index)
        solar_day = self.holiday_dates.get(name)

        if solar_day:
            self.year = solar_day.getYear()
            self.month = solar_day.getMonth()
            self.day = solar_day.getDay()
            self.update_combo_boxes()
            self.draw_calendar()


    def on_date_change(self):
        old_year = self.year
        self.year = int(self.year_combo.currentText())
        self.month = int(self.month_combo.currentText())
        self.day = 1
        if old_year != self.year:
            self.update_holiday_combo()
        self.draw_calendar()

    def go_to_today(self):
        today = datetime.now()
        current_year = int(self.year_combo.currentText())
        current_month = int(self.month_combo.currentText())

        self.year = today.year
        self.month = today.month
        self.day = today.day

        if self.year == current_year and self.month == current_month:
            self.on_day_selected(Solar.fromYmd(self.year, self.month, self.day))
        else:
            self.update_combo_boxes()

    def update_combo_boxes(self):
        old_year = int(self.year_combo.currentText())
        year_changed = self.year != old_year

        if year_changed or self.month != int(self.month_combo.currentText()):
            self.year_combo.blockSignals(True)
            self.month_combo.blockSignals(True)
            self.year_combo.setCurrentText(str(self.year))
            self.month_combo.setCurrentText(str(self.month))
            self.year_combo.blockSignals(False)
            self.month_combo.blockSignals(False)
            
            if year_changed:
                self.update_holiday_combo()

            self.draw_calendar()

    def setup_system_tray(self):
        """初始化系统托盘"""
        # 检查系统是否支持系统托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("系统不支持系统托盘")
            return

        # 获取应用程序图标
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if not os.path.exists(icon_path):
            print("找不到图标文件")
            return

        icon = QIcon(icon_path)
        if icon.isNull():
            print("无法加载图标")
            return

        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("万年历本地版")

        # 创建托盘菜单
        self.create_tray_menu()

        # 连接托盘图标的点击事件
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # 显示托盘图标
        self.tray_icon.show()

    def create_tray_menu(self):
        """创建系统托盘右键菜单"""
        tray_menu = QMenu()

        # 打开动作
        show_action = QAction("打开", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        # 开机启动动作
        autostart_action = QAction("开机启动", self)
        autostart_action.setCheckable(True)
        autostart_action.setChecked(self.is_autostart_enabled())
        autostart_action.triggered.connect(self.toggle_autostart)
        tray_menu.addAction(autostart_action)

        tray_menu.addSeparator()

        # 退出动作
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

    def on_tray_icon_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            # 双击或左键单击切换窗口显示/隐藏状态
            self.toggle_window_visibility()

    def toggle_window_visibility(self):
        """切换窗口显示/隐藏状态"""
        if self.isVisible():
            # 如果窗口当前可见，则隐藏到托盘
            self.hide_to_tray()
        else:
            # 如果窗口当前隐藏，则显示窗口
            self.show_window()

    def show_window(self):
        """显示主窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self):
        """隐藏窗口到系统托盘"""
        if self.tray_icon:
            self.hide()
            if not self.tray_icon.supportsMessages():
                return
            # 可以在这里添加提示消息
            # self.tray_icon.showMessage("万年历", "程序已在系统托盘运行", QSystemTrayIcon.Information, 2000)

    def get_autostart_desktop_file(self):
        """获取开机启动桌面文件路径"""
        return Path.home() / ".config" / "autostart" / "offlinecalendar.desktop"

    def is_autostart_enabled(self):
        """检查是否已启用开机启动"""
        desktop_file = self.get_autostart_desktop_file()
        return desktop_file.exists()

    def toggle_autostart(self, enabled):
        """切换开机启动状态"""
        desktop_file = self.get_autostart_desktop_file()

        if enabled:
            # 创建开机启动
            os.makedirs(desktop_file.parent, exist_ok=True)

            # 获取当前可执行文件的路径
            if hasattr(sys, 'frozen'):
                # PyInstaller 打包后的路径
                executable_path = sys.executable

                # 检查是否是AppImage运行
                if '/tmp/.mount_' in executable_path:
                    # 如果是临时挂载路径，尝试找到实际的AppImage文件
                    possible_paths = [
                        Path.home() / ".local" / "bin" / "万年历本地版.AppImage",
                        Path.home() / "Applications" / "万年历本地版.AppImage",
                        Path("/opt") / "万年历本地版.AppImage",
                    ]

                    # 尝试通过proc文件系统找到真实路径
                    try:
                        current_process = Path(f"/proc/{os.getpid()}/exe")
                        if current_process.exists():
                            real_exe = current_process.readlink()
                            if real_exe.endswith('.AppImage'):
                                executable_path = real_exe
                    except:
                        pass

                    # 如果找不到真实AppImage，使用第一个存在的路径
                    if '/tmp/.mount_' in executable_path:
                        for path in possible_paths:
                            if path.exists():
                                executable_path = str(path)
                                break

                        # 如果还是找不到，尝试使用当前工作目录的AppImage
                        if '/tmp/.mount_' in executable_path:
                            current_dir = Path(sys.argv[0] if sys.argv else ".").parent
                            appimage_in_current = current_dir / "万年历本地版.AppImage"
                            if appimage_in_current.exists():
                                executable_path = str(appimage_in_current)
            else:
                # 开发环境路径
                executable_path = os.path.join(os.path.dirname(__file__), "main.py")
                executable_path = f"python3 {executable_path}"

            # 获取图标路径
            if hasattr(sys, 'frozen'):
                # 对于AppImage，优先使用系统图标目录中的图标
                icon_paths = [
                    Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps" / "wannianli.png",
                    Path.home() / ".local" / "bin" / "icon.png",
                    os.path.join(os.path.dirname(executable_path), "icon.png"),
                ]

                icon_path = None
                for path in icon_paths:
                    if path.exists():
                        icon_path = str(path)
                        break

                if not icon_path:
                    icon_path = icon_paths[0]  # 使用第一个作为默认
            else:
                icon_path = os.path.join(os.path.dirname(__file__), "icon.png")

            desktop_content = f"""[Desktop Entry]
Type=Application
Name=万年历本地版
Exec={executable_path}
Icon={icon_path}
Terminal=false
Categories=Office;Calendar;
StartupNotify=true
"""

            try:
                with open(desktop_file, 'w', encoding='utf-8') as f:
                    f.write(desktop_content)
                os.chmod(desktop_file, 0o644)
                print("开机启动已启用")
            except Exception as e:
                print(f"启用开机启动失败: {e}")
                # 如果有托盘，显示错误消息
                if self.tray_icon and self.tray_icon.supportsMessages():
                    self.tray_icon.showMessage("错误", "启用开机启动失败", QSystemTrayIcon.Critical, 3000)
        else:
            # 禁用开机启动
            try:
                if desktop_file.exists():
                    desktop_file.unlink()
                print("开机启动已禁用")
            except Exception as e:
                print(f"禁用开机启动失败: {e}")
                if self.tray_icon and self.tray_icon.supportsMessages():
                    self.tray_icon.showMessage("错误", "禁用开机启动失败", QSystemTrayIcon.Critical, 3000)

    def quit_application(self):
        """完全退出应用程序"""
        # 退出Qt应用程序
        QApplication.quit()

    def closeEvent(self, event):
        """重写窗口关闭事件"""
        # 如果系统托盘可用，则隐藏到托盘而不是关闭
        if self.tray_icon and self.tray_icon.isVisible():
            event.ignore()  # 忽略关闭事件
            self.hide_to_tray()  # 隐藏到托盘
        else:
            # 如果系统托盘不可用，则正常关闭
            event.accept()
            QApplication.quit()


class ImportDialog(QDialog):
    def __init__(self, parent=None, year=2025):
        super().__init__(parent)
        self.setWindowTitle("导入假期安排")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        instructions = QLabel("请选择年份，并将该年份的假期安排文本粘贴到下方：")
        layout.addWidget(instructions)

        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("年份："))
        self.year_spinbox = QSpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(year)
        year_layout.addWidget(self.year_spinbox)
        year_layout.addStretch()
        layout.addLayout(year_layout)

        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("导入")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_data(self):
        return self.year_spinbox.value(), self.text_edit.toPlainText()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 设置应用程序信息
    app.setApplicationName("万年历本地版")
    app.setApplicationDisplayName("万年历本地版")
    app.setOrganizationName("OfflineCalendar")

    window = MainWindow()
    window.show()

    # 运行应用程序
    exit_code = app.exec()
    sys.exit(exit_code)