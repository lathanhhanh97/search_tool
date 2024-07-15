import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import subprocess

URL_LINK_ANDYTOWN = 'http://10.90.100.17:8000'

def get_current_wifi():
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True)
        output = result.stdout
        for line in output.split('\n'):
            if 'SSID' in line:
                return line.split(':')[1].strip()
    except Exception as e:
        print(f"Error getting current Wi-Fi: {e}")
    return "Unknown"

def search_sn_on_web(sn):
    # Thực hiện yêu cầu đến URL của Firefly và phân tích dữ liệu
    try:
        response = requests.get(f"http://10.90.104.16:8000/node/{sn}")
        if response.status_code != 200:
            return f"Lỗi: Không thể tìm thấy thông tin cho SN {sn}."
        return parse_html(response.text)
    except Exception as e:
        return f"Lỗi: {e}"

def search_sn_on_web_with_cookies(sn, cookies):
    # Thực hiện yêu cầu đến URL của Andytown với cookie và phân tích dữ liệu
    try:
        response = requests.get(f"{URL_LINK_ANDYTOWN}/node/{sn}", cookies=cookies)
        if response.status_code != 200:
            return f"Lỗi: Không thể tìm thấy thông tin cho SN {sn}."
        return parse_html(response.text)
    except Exception as e:
        return f"Lỗi: {e}"

def get_cookie(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Chạy ở chế độ headless
    driver = webdriver.Chrome(options=options)

    try:
        # Điều hướng đến trang đăng nhập
        driver.get(url)
        time.sleep(2)

        # Điền thông tin đăng nhập
        username_input = driver.find_element(By.ID, 'username')
        password_input = driver.find_element(By.ID, 'password')
        username_input.send_keys('luxshare')
        password_input.send_keys('bentobento')

        login_button = driver.find_element(By.CSS_SELECTOR, 'button.btn.btn-primary')
        login_button.click()
        time.sleep(2)

        # Lấy cookie sau khi đăng nhập thành công
        cookies = driver.get_cookies()
        driver.quit()
        return cookies
    except Exception as e:
        driver.quit()
        return None

def parse_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'class': 'failures'})
    if not table:
        return "Không tìm thấy bảng dữ liệu."

    data = []
    rows = table.find_all('tr', class_='danger')
    for row in rows:
        cells = row.find_all(['th', 'td'])
        row_data = [cell.get_text(strip=True) for cell in cells]
        
        # Lấy thông tin link từ cột cuối cùng
        links = row.find_all('a')
        link_texts = []
        link_hrefs = []
        for link in links:
            link_texts.append(link.text)
            link_hrefs.append(URL_LINK_ANDYTOWN + link['href'])
        row_data.extend(link_texts + link_hrefs)

        data.append(row_data)
    return data
