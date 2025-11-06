import sys
import re
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, Signal, QSettings, QTimer
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

        # 设置定时器用于日期更新
        self.setup_date_timer()

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

        # 解析所有节假日行
        all_vacation_days = []
        all_work_days = []
        holiday_names_list = []  # 用于界面下拉框的节假日名称列表

        # 按行解析，支持任意中文数字（一、二、三...十）
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配格式：[中文数字]、[节日名]：[安排文本]
            holiday_match = re.match(r'^([一二三四五六七八九十]+)、([^：]+)：(.+)$', line)
            if not holiday_match:
                continue

            chinese_number, holiday_name, arrangement = holiday_match.groups()
            holiday_name = holiday_name.strip()
            arrangement = arrangement.strip()

            # 添加到节假日名称列表（用于界面下拉框）
            holiday_names_list.append(holiday_name)

            # 分割安排文本：放假日期文本 和 调休文本
            parts = arrangement.split('。', 1)  # 按第一个句号分割
            vacation_text = parts[0]
            adjust_text = parts[1] if len(parts) > 1 else ""

            # 从放假日期文本中提取日期范围
            vacation_dates = self._extract_vacation_dates(vacation_text, year)

            # 从调休文本中提取上班日（仅当有调休文本时）
            if adjust_text:
                work_dates = self._extract_work_days(adjust_text, year)
                all_work_days.extend(work_dates)

            # 为每个节假日添加假期日期
            # 注意：这里直接使用原始节日名称，不做映射
            for date_obj in vacation_dates:
                all_vacation_days.append((date_obj, holiday_name))

        # 为界面下拉框提供节假日名称
        self.available_holidays = sorted(list(set(holiday_names_list)))

        # 生成数据字符串
        for date_obj, holiday_name in all_vacation_days:
            # 尝试映射到HolidayUtil的标准名称，如果无法映射则跳过
            name_index = name_to_index.get(holiday_name)
            if name_index is None:
                # 尝试常见映射
                mapping = {
                    "元旦": "元旦节",
                    "春节": "春节",
                    "清明节": "清明节",
                    "劳动节": "劳动节",
                    "端午节": "端午节",
                    "中秋节": "中秋节",
                    "国庆节": "国庆节",
                    "国庆节、中秋节": "国庆中秋",
                    "中秋节、国庆节": "国庆中秋"
                }
                name_index = name_to_index.get(mapping.get(holiday_name))
                if name_index is None:
                    continue

            day_str = date_obj.strftime("%Y%m%d")
            target_date_str = day_str
            data_string += f"{day_str}{name_index}1{target_date_str}"

        # 为每个上班日找到对应的节假日
        work_to_holiday = {}
        for work_date in all_work_days:
            # 查找最近的节假日
            closest_holiday = None
            min_distance = float('inf')

            for vac_date, vac_name in all_vacation_days:
                distance = abs((work_date - vac_date).days)
                if distance < min_distance and distance <= 30:  # 30天内的上班日才关联
                    min_distance = distance
                    closest_holiday = vac_name

            if closest_holiday:
                work_to_holiday[work_date] = closest_holiday

        for work_date, holiday_name in work_to_holiday.items():
            # 映射到HolidayUtil的标准名称
            mapping = {
                "元旦": "元旦节",
                "春节": "春节",
                "清明节": "清明节",
                "劳动节": "劳动节",
                "端午节": "端午节",
                "中秋节": "中秋节",
                "国庆节": "国庆节",
                "国庆节、中秋节": "国庆中秋",
                "中秋节、国庆节": "国庆中秋"
            }
            mapped_holiday = mapping.get(holiday_name)
            if mapped_holiday:
                name_index = name_to_index.get(mapped_holiday)
                if name_index is not None:
                    day_str = work_date.strftime("%Y%m%d")
                    # 找到对应的假期第一天作为目标日期
                    target_date_str = None
                    for vac_date, vac_name in all_vacation_days:
                        if vac_name == holiday_name:
                            target_date_str = vac_date.strftime("%Y%m%d")
                            break
                    if target_date_str:
                        data_string += f"{day_str}{name_index}0{target_date_str}"

        return data_string

    def _extract_vacation_dates(self, vacation_text, year):
        """
        从放假日期文本中提取所有日期

        Args:
            vacation_text (str): 放假日期文本部分
            year (int): 年份

        Returns:
            list: datetime 对象列表
        """
        dates = []

        # 清理文本，去掉括号内容和无关描述
        cleaned_text = re.sub(r'（[^）]*）', '', vacation_text)
        cleaned_text = re.sub(r'\([^)]*\)', '', cleaned_text)
        cleaned_text = re.sub(r'放假调休，共\d+天', '', cleaned_text)
        cleaned_text = re.sub(r'放假，共\d+天', '', cleaned_text)

        # 多种日期格式模式，按优先级排序
        patterns = [
            # 跨年格式：2022年12月31日至2023年1月2日
            (r'(\d{4})年(\d+)月(\d+)日至(\d{4})年(\d+)月(\d+)日', 'cross_year'),
            # 跨月格式：1月28日至2月4日
            (r'(\d+)月(\d+)日至(\d+)月(\d+)日', 'cross_month'),
            # 同月跨日格式：4月4日至6日
            (r'(\d+)月(\d+)日至(\d+)日', 'same_month'),
            # 单日格式：1月1日
            (r'(\d+)月(\d+)日', 'single_day')
        ]

        for pattern, pattern_type in patterns:
            matches = re.findall(pattern, cleaned_text)
            if not matches:
                continue

            for match in matches:
                try:
                    if pattern_type == 'cross_year':
                        start_date = datetime(int(match[0]), int(match[1]), int(match[2]))
                        end_date = datetime(int(match[3]), int(match[4]), int(match[5]))
                    elif pattern_type == 'cross_month':
                        start_date = datetime(year, int(match[0]), int(match[1]))
                        end_date = datetime(year, int(match[2]), int(match[3]))
                    elif pattern_type == 'same_month':
                        start_date = datetime(year, int(match[0]), int(match[1]))
                        end_date = datetime(year, int(match[0]), int(match[2]))
                    elif pattern_type == 'single_day':
                        start_date = datetime(year, int(match[0]), int(match[1]))
                        end_date = start_date

                    # 生成日期范围
                    current_date = start_date
                    while current_date <= end_date:
                        if current_date not in dates:  # 避免重复
                            dates.append(current_date)
                        current_date += timedelta(days=1)

                except (ValueError, TypeError, IndexError):
                    continue

            # 如果找到了匹配，就不再尝试其他模式
            if matches:
                break

        return sorted(dates)

    def _extract_work_days(self, adjust_text, year):
        """
        从调休文本中提取上班日期

        Args:
            adjust_text (str): 调休文本部分
            year (int): 年份

        Returns:
            list: datetime 对象列表
        """
        work_dates = []

        # 清理文本，去掉最后的句号
        cleaned_text = adjust_text.rstrip('。')

        # 先尝试直接匹配包含"上班"的日期
        direct_patterns = [
            r'(\d+)月(\d+)日（?(?:星期|周)?[一二三四五六日日]?）?\s*上班',
            r'(\d+)月(\d+)日\([^)]*\)\s*上班',
            r'(\d+)月(\d+)日（[^）]*）\s*上班',
            r'(\d+)月(\d+)日\s*上班'
        ]

        for pattern in direct_patterns:
            matches = re.findall(pattern, cleaned_text)
            for month, day in matches:
                try:
                    work_date = datetime(year, int(month), int(day))
                    if work_date not in work_dates:  # 避免重复
                        work_dates.append(work_date)
                except (ValueError, TypeError, IndexError):
                    continue

        # 然后处理"X月X日（周X）、X月X日上班"这种格式
        # 将文本按逗号分割，检查每段是否包含上班信息
        parts = re.split(r'[，、]', cleaned_text)
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            # 如果当前部分包含"上班"，已经处理过了
            if '上班' in part:
                continue

            # 如果当前部分不包含"上班"，但下一部分包含"上班"，
            # 那么当前部分可能也是上班日
            if i + 1 < len(parts) and '上班' in parts[i + 1]:
                # 尝试从当前部分提取日期
                date_pattern = r'(\d+)月(\d+)日（?(?:星期|周)?[一二三四五六日日]?）?'
                matches = re.findall(date_pattern, part)
                for month, day in matches:
                    try:
                        work_date = datetime(year, int(month), int(day))
                        if work_date not in work_dates:  # 避免重复
                            work_dates.append(work_date)
                    except (ValueError, TypeError, IndexError):
                        continue

        return sorted(work_dates)

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

        # 优先使用导入的自定义节假日，如果没有则使用默认节假日
        holiday_names = getattr(self, 'available_holidays', None)

        if holiday_names:
            # 使用导入的节假日名称
            for name in holiday_names:
                if name not in self.holiday_dates:
                    # 查找该节假日的第一天作为代表日期
                    # 这里可以根据需要进一步优化
                    holidays = HolidayUtil.getHolidays(self.year)
                    if holidays:
                        for h in holidays:
                            if not h.isWork() and h.getDay() == h.getTarget():
                                holiday_name = h.getName()
                                # 简单的名称匹配，可以改进
                                if name in holiday_name or holiday_name in name:
                                    date_str = h.getDay()
                                    parts = date_str.split('-')
                                    year = int(parts[0])
                                    month = int(parts[1])
                                    day = int(parts[2])
                                    self.holiday_dates[name] = Solar.fromYmd(year, month, day)
                                    break
        else:
            # 使用默认的节假日
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
        # 强制跳转到当前日期
        today = datetime.now()
        self.year = today.year
        self.month = today.month
        self.day = today.day
        self.update_combo_boxes()
        self.draw_calendar()

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
        autostart_action.triggered.connect(lambda checked: self.toggle_autostart(checked))
        tray_menu.addAction(autostart_action)

        # 静默启动动作
        silent_autostart_action = QAction("静默启动", self)
        silent_autostart_action.setCheckable(True)
        silent_autostart_action.setChecked(self.is_silent_autostart_enabled())
        silent_autostart_action.triggered.connect(lambda checked: self.toggle_silent_autostart(checked))
        tray_menu.addAction(silent_autostart_action)

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
        # 显示窗口前先检查并更新日期（使用智能检查）
        self.check_date_on_show()
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

    def is_silent_autostart_enabled(self):
        """检查是否已启用静默启动"""
        return self.settings.value("silent_autostart", False, type=bool)

    def toggle_silent_autostart(self, enabled):
        """切换静默启动设置"""
        self.settings.setValue("silent_autostart", enabled)

        # 如果开机启动已启用，则更新desktop文件以应用新的设置
        if self.is_autostart_enabled():
            print(f"静默启动设置已更新: {'启用' if enabled else '禁用'}")
            # 重新生成开机启动文件
            self.update_autostart_file()
        else:
            print("请先启用开机启动功能")

    def update_autostart_file(self):
        """更新开机启动文件"""
        desktop_file = self.get_autostart_desktop_file()
        if desktop_file.exists():
            # 删除现有文件并重新创建
            try:
                desktop_file.unlink()
                self.toggle_autostart(True)
            except Exception as e:
                print(f"更新开机启动文件失败: {e}")

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

            # 为开机启动添加静默启动参数
            silent_enabled = self.is_silent_autostart_enabled()
            if hasattr(sys, 'frozen') and '/tmp/.mount_' not in executable_path and silent_enabled:
                # AppImage 或其他打包版本且启用静默启动时，添加静默启动参数
                exec_command = f"{executable_path} --silent"
            else:
                # 其他情况不添加静默参数
                exec_command = executable_path

            desktop_content = f"""[Desktop Entry]
Type=Application
Name=万年历本地版
Exec={exec_command}
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

    def setup_date_timer(self):
        """设置日期更新定时器"""
        # 注释掉每分钟检查的定时器，避免自动跳转
        # self.date_timer = QTimer(self)
        # self.date_timer.timeout.connect(self.check_and_update_date)
        # self.date_timer.start(60000)  # 60秒 = 1分钟

        # 只保留午夜精确刷新定时器
        self.schedule_midnight_refresh()

    def schedule_midnight_refresh(self):
        """安排午夜精确刷新"""
        self.midnight_timer = QTimer(self)
        self.midnight_timer.setSingleShot(True)
        self.midnight_timer.timeout.connect(self.on_midnight_refresh)

        # 计算到下一个午夜的时间
        now = datetime.now()
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        time_until_midnight = (tomorrow - now).total_seconds() * 1000  # 转换为毫秒

        self.midnight_timer.start(int(time_until_midnight))

    def on_midnight_refresh(self):
        """午夜刷新处理"""
        self.refresh_calendar()
        # 重新安排下一个午夜刷新
        self.schedule_midnight_refresh()

    def check_and_update_date(self):
        """检查日期是否发生变化，如果变化则显示提示"""
        today = datetime.now()
        current_date = today.strftime("%Y-%m-%d")

        # 获取当前存储的日期
        stored_date = f"{self.year}-{self.month:02d}-{self.day:02d}"

        if current_date != stored_date:
            # 日期已变化，但不再自动切换，只在状态栏显示提示
            # 如果当前显示的不是今天，可以在状态栏显示一个提示
            # 或者完全忽略，让用户手动切换
            pass  # 不做自动切换，保持用户当前查看的月份

    def refresh_calendar(self):
        """刷新日历显示，但保持用户当前查看的月份"""
        today = datetime.now()

        # 只有当用户当前正在查看今天的月份时才更新到今天
        if self.year == today.year and self.month == today.month:
            self.year = today.year
            self.month = today.month
            self.day = today.day
            self.update_combo_boxes()
            self.draw_calendar()
        else:
            # 如果用户正在查看其他月份，只刷新日历显示但不改变月份
            self.draw_calendar()

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

    def showEvent(self, event):
        """重写窗口显示事件，在窗口显示时检查日期"""
        super().showEvent(event)
        self.check_date_on_show()

    def check_date_on_show(self):
        """在窗口显示时检查是否需要更新日期"""
        today = datetime.now()
        current_date = today.strftime("%Y-%m-%d")
        stored_date = f"{self.year}-{self.month:02d}-{self.day:02d}"

        # 如果存储的日期不是今天，说明可能已经跨天了
        if current_date != stored_date:
            # 如果用户当前查看的月份不是今天的月份，不做自动切换
            # 如果用户正在查看今天的月份但日期不对，则更新到今天
            if self.year == today.year and self.month == today.month:
                self.year = today.year
                self.month = today.month
                self.day = today.day
                self.update_combo_boxes()
                self.draw_calendar()
            # 如果用户查看的是其他月份，保持不变，让用户手动切换


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

    # 检查是否为静默启动模式
    silent_start = "--silent" in sys.argv or "--tray" in sys.argv

    window = MainWindow()

    # 如果不是静默启动，则显示主窗口
    if not silent_start:
        window.show()
    else:
        # 静默启动时，确保窗口最小化到托盘
        if window.tray_icon and window.tray_icon.isVisible():
            print("静默启动模式，程序已在系统托盘运行")
        else:
            # 如果系统不支持托盘，仍然显示窗口
            print("系统不支持托盘，显示主窗口")
            window.show()

    # 运行应用程序
    exit_code = app.exec()
    sys.exit(exit_code)