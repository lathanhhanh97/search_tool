from bs4 import BeautifulSoup

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
        links = row.find_all('a')
        link_strs = [f"<a href='{link['href']}'>{link.text}</a>" for link in links if link.has_attr('href')]
        links_text = '<br>'.join(link_strs)
        data.append([test_name] + cols + [links_text])  # Thêm tất cả các cột và links vào cuối
    print(f"Parsed data: {data}")
    return data
