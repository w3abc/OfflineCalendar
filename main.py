import sys
from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
    QGridLayout, QPushButton, QComboBox, QFrame
)
from lunar_python import Solar, SolarMonth
from lunar_python.util import HolidayUtil

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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("离线日历")
        self.setGeometry(100, 100, 1100, 700)
        self.selected_cell = None
        self.app = QApplication.instance()

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
        self.today_button.clicked.connect(self.go_to_today)

        # --- Initial Draw & Style ---
        self.setup_styles()
        self.update_combo_boxes()
        self.draw_calendar()

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
        self.today_button = QPushButton("今天")

        controls_layout.addWidget(self.year_combo)
        controls_layout.addWidget(QLabel("年"))
        controls_layout.addWidget(self.month_combo)
        controls_layout.addWidget(QLabel("月"))
        controls_layout.addStretch()
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

    def on_date_change(self):
        self.year = int(self.year_combo.currentText())
        self.month = int(self.month_combo.currentText())
        self.day = 1
        self.draw_calendar()

    def go_to_today(self):
        today = datetime.now()
        self.year = today.year
        self.month = today.month
        self.day = today.day
        self.update_combo_boxes()

    def update_combo_boxes(self):
        if self.year != int(self.year_combo.currentText()) or self.month != int(self.month_combo.currentText()):
            self.year_combo.blockSignals(True)
            self.month_combo.blockSignals(True)
            self.year_combo.setCurrentText(str(self.year))
            self.month_combo.setCurrentText(str(self.month))
            self.year_combo.blockSignals(False)
            self.month_combo.blockSignals(False)
            self.draw_calendar()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())