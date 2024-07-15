import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                             QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem, QSplitter, QFormLayout, QStatusBar, QFileDialog)
from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt
from PyQt5.QtGui import QFont, QPixmap, QIcon, QDesktopServices, QMovie
from PyQt5.QtCore import QUrl
from .worker import Worker
from .network import get_current_wifi, search_sn_on_web, search_sn_on_web_with_cookies, get_cookie
import pandas as pd
from datetime import datetime

URL_LINK_ANDYTOWN = 'http://10.90.100.17:8000'

class FadeLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._opacity = 1.0
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(1000)  # 1 second duration
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.setStyleSheet(f"color: rgba(0, 123, 255, {value * 255});")

    def fadeIn(self):
        self.animation.start()

class WifiWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.cookies = None
        self.current_wifi = ""  # Khởi tạo biến để lưu tên Wi-Fi hiện tại
        self.initUI()
        self.refresh_wifi_thread()  # Gọi hàm refresh_wifi_thread khi khởi tạo

    def initUI(self):
        self.setWindowTitle('SEARCH TOOL')
        self.setGeometry(100, 100, 1200, 800)

        font = QFont("Arial", 18)

        main_layout = QVBoxLayout()

        # Tạo QSplitter để chia không gian giữa Wi-Fi info và SN lookup
        splitter = QSplitter(Qt.Vertical)

        # GroupBox cho Wi-Fi Info
        wifi_group = QGroupBox()
        wifi_group.setFont(font)
        wifi_layout = QHBoxLayout()
        
        # Layout bên trái cho "SEARCH TOOL" và Wi-Fi hiện tại
        left_layout = QVBoxLayout()
        title_label = QLabel("SEARCH TOOL")
        title_font = QFont("Arial", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignLeft)
        left_layout.addWidget(title_label)

        wifi_info_layout = QVBoxLayout()
        self.wifi_label = FadeLabel('Wi-Fi: ')
        wifi_font = QFont("Arial", 14)  # Đặt kích thước font nhỏ hơn cho Wi-Fi info
        self.wifi_label.setFont(wifi_font)
        wifi_info_layout.addWidget(self.wifi_label)
        wifi_info_layout.addStretch()
        left_layout.addLayout(wifi_info_layout)
        wifi_layout.addLayout(left_layout)

        # Thêm logo vào góc bên phải
        self.logo_label = QLabel(self)
        logo_pixmap = QPixmap('assets/logo.png')
        self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setScaledContents(True)
        self.logo_label.setFixedSize(350, 100)  # Đặt kích thước logo
        wifi_layout.addWidget(self.logo_label, alignment=Qt.AlignRight)
        
        wifi_group.setLayout(wifi_layout)
        splitter.addWidget(wifi_group)

        # GroupBox cho Tra cứu SN
        sn_group = QGroupBox("CHECK INFO")
        sn_group.setFont(font)
        sn_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.sn_input = QLineEdit(self)
        self.sn_input.setPlaceholderText('Nhập SN')
        self.sn_input.setFont(font)
        self.sn_input.setStyleSheet("background-color: #f0f0f0; color: #333; padding: 5px;")
        form_layout.addRow("SN:", self.sn_input)
        
        self.lookup_button = QPushButton('SEARCH', self)
        self.lookup_button.setFont(font)
        self.lookup_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 20px;")
        self.lookup_button.setIcon(QIcon.fromTheme("search"))
        self.lookup_button.clicked.connect(self.lookup_sn_thread)
        form_layout.addRow("", self.lookup_button)

        sn_layout.addLayout(form_layout)
        
        self.product_info_table = QTableWidget()
        self.product_info_table.setColumnCount(9)
        self.product_info_table.setHorizontalHeaderLabels(['Test Name', 'Value', 'Time', 'Station', 'Run', 'Error Code', 'Test Software', 'Link 1', 'Link 2'])
        self.product_info_table.horizontalHeader().setStretchLastSection(True)
        self.product_info_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #f0f0f0;
                font-size: 16px;
                border: 1px solid #ddd;
                padding: 5px;
            }
        """)
        self.product_info_table.setStyleSheet("""
            QTableWidget::item {
                padding: 10px;
                font-size: 16px;
                border: 1px solid #ddd;
            }
            QTableWidget::item:selected {
                background-color: #e0e0e0;
            }
        """)
        self.product_info_table.cellClicked.connect(self.cell_clicked)
        sn_layout.addWidget(self.product_info_table)

        # Spinner
        self.spinner_label = QLabel(self)
        self.spinner = QMovie("assets/spinner.gif")
        self.spinner_label.setMovie(self.spinner)
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_label.setVisible(False)
        sn_layout.addWidget(self.spinner_label)

        # Button xuất file Excel
        self.export_button = QPushButton('Export to Excel', self)
        self.export_button.setFont(font)
        self.export_button.setStyleSheet("background-color: #007BFF; color: white; padding: 10px 20px;")
        self.export_button.clicked.connect(self.export_to_excel)
        sn_layout.addWidget(self.export_button)

        sn_group.setLayout(sn_layout)
        splitter.addWidget(sn_group)

        main_layout.addWidget(splitter)

        # Thêm một thanh trạng thái để hiển thị thông tin trạng thái và lỗi
        self.status_bar = QStatusBar(self)
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

        # Thiết lập QTimer cho chức năng auto-refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_wifi_thread)
        self.timer.start(5000)  # Làm mới mỗi 5 giây

        # Đặt ảnh nền
        self.set_background()

    def set_background(self):
        # Load the image
        background_image = QPixmap('assets/background.png')
        if background_image.isNull():
            print("Could not load image.")
            return

        # Create QLabel to display the background image
        self.background_label = QLabel(self)
        self.background_label.setPixmap(background_image)
        self.background_label.setScaledContents(True)
        self.background_label.setGeometry(self.rect())

        # Move the background QLabel to the bottom layer
        self.background_label.lower()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'background_label'):
            self.background_label.setGeometry(self.rect())

    def refresh_wifi_thread(self):
        print("Refreshing Wi-Fi info...")
        self.worker = Worker(get_current_wifi)
        self.worker.result_ready.connect(self.update_wifi_info)
        self.worker.error_occurred.connect(lambda e: self.show_error_message("Lỗi Wi-Fi", e))
        self.worker.start()

    def update_wifi_info(self, info):
        print(f"Updated Wi-Fi info: {info}")
        self.wifi_label.setText('Wi-Fi hiện tại: ' + info)
        self.wifi_label.fadeIn()
        self.current_wifi = info  # Lưu lại thông tin Wi-Fi hiện tại

    def lookup_sn_thread(self):
        self.timer.stop()  # Dừng auto-refresh Wi-Fi info khi tra cứu
        sn = self.sn_input.text()
        if not sn:
            self.show_error_message("Lỗi", "Vui lòng nhập SN")
            self.timer.start()  # Bắt đầu lại auto-refresh nếu không có SN
            return

        print(f"Looking up SN: {sn}")
        self.spinner_label.setVisible(True)  # Hiển thị spinner
        self.spinner.start()

        if "firefly" in self.current_wifi.lower():
            print("Using Firefly link")
            self.worker = Worker(search_sn_on_web, sn)
        elif "andytown" in self.current_wifi.lower():
            print("Using Andytown link")
            if self.cookies is None:
                print("No cookies found, logging in...")
                self.worker = Worker(get_cookie, f"{URL_LINK_ANDYTOWN}/auth/login")
                self.worker.result_ready.connect(self.update_cookies_and_search)
                self.worker.error_occurred.connect(lambda e: self.show_error_message("Lỗi Đăng nhập", e))
                self.worker.start()
                return
            print("Using existing cookies")
            self.worker = Worker(search_sn_on_web_with_cookies, sn, self.cookies)
        else:
            self.spinner_label.setVisible(False)  # Ẩn spinner nếu có lỗi
            self.spinner.stop()
            self.show_error_message("Lỗi", "Không xác định được Wi-Fi hiện tại")
            self.timer.start()  # Bắt đầu lại auto-refresh nếu có lỗi
            return

        self.worker.result_ready.connect(self.update_product_info)
        self.worker.error_occurred.connect(lambda e: self.show_error_message("Lỗi Tra cứu SN", e))
        self.worker.finished.connect(self.on_lookup_finished)
        self.worker.start()

    def update_cookies_and_search(self, cookies):
        if cookies is None:
            self.show_error_message("Lỗi Đăng nhập", "Không thể đăng nhập vào hệ thống Andytown")
            self.spinner_label.setVisible(False)  # Ẩn spinner nếu có lỗi
            self.spinner.stop()
            self.timer.start()  # Bắt đầu lại auto-refresh nếu có lỗi
            return

        print("Cookies received, proceeding with search")
        self.cookies = cookies
        sn = self.sn_input.text()
        self.worker = Worker(search_sn_on_web_with_cookies, sn, self.cookies)
        self.worker.result_ready.connect(self.update_product_info)
        self.worker.error_occurred.connect(lambda e: self.show_error_message("Lỗi Tra cứu SN", e))
        self.worker.finished.connect(self.on_lookup_finished)
        self.worker.start()

    def on_lookup_finished(self):
        self.spinner_label.setVisible(False)  # Ẩn spinner khi hoàn thành
        self.spinner.stop()
        self.timer.start()  # Bắt đầu lại auto-refresh sau khi tra cứu xong

    def update_product_info(self, data):
        print(f"Updating product info with data: {data}")
        if isinstance(data, str):
            self.show_error_message("Thông báo", data)
        else:
            self.product_info_table.setRowCount(len(data))
            self.product_info_table.clearContents()
            for row_index, row_data in enumerate(data):
                for col_index, col_data in enumerate(row_data[:7]):
                    item = QTableWidgetItem(col_data)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.product_info_table.setItem(row_index, col_index, item)

                # Handle the links
                link1_text, link1_href = row_data[7], row_data[9]
                link2_text, link2_href = row_data[8], row_data[10]
                
                if link1_href:
                    link1_item = QTableWidgetItem(link1_text)
                    link1_item.setToolTip(URL_LINK_ANDYTOWN + link1_href)
                    link1_item.setTextAlignment(Qt.AlignCenter)
                    self.product_info_table.setItem(row_index, 7, link1_item)
                else:
                    self.product_info_table.setItem(row_index, 7, QTableWidgetItem(''))

                if link2_href:
                    link2_item = QTableWidgetItem(link2_text)
                    link2_item.setToolTip(URL_LINK_ANDYTOWN + link2_href)
                    link2_item.setTextAlignment(Qt.AlignCenter)
                    self.product_info_table.setItem(row_index, 8, link2_item)
                else:
                    self.product_info_table.setItem(row_index, 8, QTableWidgetItem(''))

            self.product_info_table.resizeColumnsToContents()
            self.product_info_table.horizontalHeader().setStretchLastSection(True)

    def cell_clicked(self, row, column):
        if column == 7 or column == 8:  # Link columns
            item = self.product_info_table.item(row, column)
            if item and item.toolTip():
                url = item.toolTip()
                QDesktopServices.openUrl(QUrl(url))

    def show_error_message(self, title, message):
        print(f"Error: {title} - {message}")
        self.status_bar.showMessage(message, 5000)  # Hiển thị thông báo lỗi trong 5 giây
        error_msg = QMessageBox()
        error_msg.setIcon(QMessageBox.Critical)
        error_msg.setWindowTitle(title)
        error_msg.setText(message)
        error_msg.exec_()

    def export_to_excel(self):
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        sn = self.sn_input.text()
        filename, _ = QFileDialog.getSaveFileName(self, "Save File", f"{sn}_{current_time}.xlsx", "Excel Files (*.xlsx)")
        if filename:
            data = []
            for row in range(self.product_info_table.rowCount()):
                row_data = []
                for column in range(self.product_info_table.columnCount()):
                    item = self.product_info_table.item(row, column)
                    if item:
                        row_data.append(item.text())
                    else:
                        row_data.append("")
                data.append(row_data)
            df = pd.DataFrame(data, columns=[self.product_info_table.horizontalHeaderItem(i).text() for i in range(self.product_info_table.columnCount())])
            df.to_excel(filename, index=False)
            self.show_error_message("Thông báo", f"Dữ liệu đã được xuất thành công tới {filename}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WifiWidget()
    window.show()
    sys.exit(app.exec_())
