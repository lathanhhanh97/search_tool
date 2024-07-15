import sys
import subprocess
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                             QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem, QProgressBar, QSplitter, QFormLayout, QStatusBar)
from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

URL_LINK_FIREFLY = 'http://10.90.104.16:8000'
URL_LINK_ANDYTOWN = 'http://10.90.100.17:8000'

class Worker(QThread):
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

def get_current_wifi():
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if 'SSID' in line and 'BSSID' not in line:
                ssid = line.split(':')[1].strip().lower()
                return ssid
        return "không có kết nối wi-fi"
    except subprocess.CalledProcessError as e:
        return f"Lỗi khi lấy thông tin Wi-Fi: {e}"
    except Exception as e:
        return f"Lỗi không xác định: {e}"

def get_cookie(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Optional: run headless
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print(f"Navigating to login page: {url}")
        driver.get(url)
        time.sleep(2)

        print("Finding username input field")
        username_input = driver.find_element(By.ID, 'username')
        print("Finding password input field")
        password_input = driver.find_element(By.ID, 'password')

        print("Entering username and password")
        username_input.send_keys('luxshare')
        password_input.send_keys('bentobento')

        print("Finding and clicking login button")
        login_button = driver.find_element(By.CSS_SELECTOR, 'button.btn.btn-primary')
        login_button.click()
        time.sleep(5)

        print("Checking login success")
        # Check if login was successful
        if "login" in driver.current_url:
            print("Login failed, still on login page.")
            driver.quit()
            return None

        print("Retrieving cookies after login")
        cookies = driver.get_cookies()
        driver.quit()
        print(f"Cookies retrieved: {cookies}")
        return cookies
    except Exception as e:
        driver.quit()
        print("An error occurred during login:", e)
        return None

def search_sn_on_web_with_cookies(sn, cookies):
    print(f"Starting search with cookies for SN: {sn}")
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    url = f"{URL_LINK_ANDYTOWN}/node/{sn}"
    print(f"Requesting URL: {url}")
    response = session.get(url)
    print(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        return parse_failed_tests(response.text)
    else:
        return f"Lỗi khi kết nối đến trang web: {response.status_code}"

def search_sn_on_web(sn):
    print(f"Starting search for SN: {sn}")
    url = f"{URL_LINK_FIREFLY}/node/{sn}"
    print(f"Requesting URL: {url}")
    response = requests.get(url)
    print(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        return parse_failed_tests(response.text)
    else:
        return f"Lỗi khi kết nối đến trang web: {response.status_code}"

def parse_failed_tests(html):
    print("Parsing HTML...")
    soup = BeautifulSoup(html, 'html.parser')
    
    error_message = soup.find('h3', {'class': 'eero-font quotepad warning-text'})
    if error_message and "Invalid node serial" in error_message.text:
        return "SN không hợp lệ hoặc không tìm thấy."
    
    failed_tests_section = soup.find('div', {'id': 'failed-phases'})
    if not failed_tests_section:
        print("Không tìm thấy mục 'failed-phases'")
        return "Không tìm thấy thông tin cho SN đã nhập."
    
    failed_tests_table = failed_tests_section.find('table', {'class': 'failures'})
    if not failed_tests_table:
        print("Không tìm thấy bảng 'failures'")
        return "Không tìm thấy thông tin cho SN đã nhập."
    
    rows = failed_tests_table.find('tbody').find_all('tr')
    data = []
    for row in rows:
        test_name = row.find('th').text.strip()
        cols = row.find_all('td')
        cols = [col.text.strip() for col in cols]
        data.append([test_name] + cols[:-1])  # Bỏ cột Test Image
    print(f"Parsed data: {data}")
    return data

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

    def initUI(self):
        self.setWindowTitle('Wi-Fi Hiện Tại và Tra Cứu SN')
        self.setGeometry(100, 100, 1000, 700)

        font = QFont("Arial", 18)

        main_layout = QVBoxLayout()

        # Tạo QSplitter để chia không gian giữa Wi-Fi info và SN lookup
        splitter = QSplitter(Qt.Vertical)

        # GroupBox cho Wi-Fi Info
        wifi_group = QGroupBox("Thông tin Wi-Fi hiện tại")
        wifi_group.setFont(font)
        wifi_layout = QVBoxLayout()
        self.wifi_label = FadeLabel('Wi-Fi hiện tại: ' + get_current_wifi())
        self.wifi_label.setFont(font)
        wifi_layout.addWidget(self.wifi_label)
        wifi_group.setLayout(wifi_layout)
        splitter.addWidget(wifi_group)

        # GroupBox cho Tra cứu SN
        sn_group = QGroupBox("Tra cứu thông tin sản phẩm")
        sn_group.setFont(font)
        sn_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.sn_input = QLineEdit(self)
        self.sn_input.setPlaceholderText('Nhập SN tại đây')
        self.sn_input.setFont(font)
        self.sn_input.setStyleSheet("background-color: #f0f0f0; color: #333;")
        form_layout.addRow("SN:", self.sn_input)
        
        self.lookup_button = QPushButton('Tra cứu SN', self)
        self.lookup_button.setFont(font)
        self.lookup_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.lookup_button.setIcon(QIcon.fromTheme("search"))
        self.lookup_button.clicked.connect(self.lookup_sn_thread)
        form_layout.addRow("", self.lookup_button)

        sn_layout.addLayout(form_layout)
        
        self.product_info_table = QTableWidget()
        self.product_info_table.setColumnCount(6)
        self.product_info_table.setHorizontalHeaderLabels(['Test Name', 'Value', 'Time', 'Station', 'Run', 'Error Code', 'Test Software'])
        self.product_info_table.horizontalHeader().setStretchLastSection(True)
        self.product_info_table.horizontalHeader().setStyleSheet("background-color: #f0f0f0; font-size: 16px;")
        self.product_info_table.setStyleSheet("QTableWidget::item { padding: 5px; font-size: 16px; } QHeaderView::section { background-color: #f0f0f0; font-size: 16px; }")
        sn_layout.addWidget(self.product_info_table)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setVisible(False)
        sn_layout.addWidget(self.progress_bar)
        
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
        background_image = QPixmap('background.png')
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
        self.progress_bar.setVisible(True)  # Hiển thị progress bar

        if "firefly" in self.current_wifi:
            print("Using Firefly link")
            self.worker = Worker(search_sn_on_web, sn)
        elif "andytown" in self.current_wifi:
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
            self.progress_bar.setVisible(False)  # Ẩn progress bar nếu có lỗi
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
            self.progress_bar.setVisible(False)  # Ẩn progress bar nếu có lỗi
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
        self.progress_bar.setVisible(False)  # Ẩn progress bar khi hoàn thành
        self.timer.start()  # Bắt đầu lại auto-refresh sau khi tra cứu xong

    def update_product_info(self, data):
        print(f"Updating product info with data: {data}")
        if isinstance(data, str):
            self.show_error_message("Thông báo", data)
        else:
            self.product_info_table.setRowCount(len(data))
            self.product_info_table.clearContents()
            for row_index, row_data in enumerate(data):
                for col_index, col_data in enumerate(row_data):
                    item = QTableWidgetItem(col_data)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.product_info_table.setItem(row_index, col_index, item)
            self.product_info_table.resizeColumnsToContents()
            self.product_info_table.horizontalHeader().setStretchLastSection(True)  # Ensure last column stretches

    def show_error_message(self, title, message):
        print(f"Error: {title} - {message}")
        self.status_bar.showMessage(message, 5000)  # Hiển thị thông báo lỗi trong 5 giây
        error_msg = QMessageBox()
        error_msg.setIcon(QMessageBox.Critical)
        error_msg.setWindowTitle(title)
        error_msg.setText(message)
        error_msg.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    wifi_widget = WifiWidget()
    wifi_widget.show()
    sys.exit(app.exec_())
