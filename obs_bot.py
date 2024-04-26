import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from xml.etree.ElementTree import Element, SubElement, ElementTree

class WebScraperApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Web Scraper")
        self.setGeometry(100, 100, 400, 250)

        self.init_ui()

    def init_ui(self):
        #TC
        self.username_label = QLabel("TC Kimlik Numarası:")
        self.username_input = QLineEdit()

        # Şifre
        self.password_label = QLabel("Şifre:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        # Çalıştırma Butonu
        self.run_button = QPushButton("Notları Kaydet ve Gönder")
        self.run_button.clicked.connect(self.run_web_scraper)

        # Durum Etiketi
        self.status_label = QLabel("")

        # Düzen
        layout = QVBoxLayout()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def run_web_scraper(self):
        # Kullanıcı adı, şifre ve emaili al
        username = self.username_input.text()
        password = self.password_input.text()
        url = "https://obs.ahievran.edu.tr/oibs/ogrenci/login.aspx"

        if not username or not password:
            self.status_label.setText("Lütfen TC kimlik numaranızı, e-devlet şifrenizi ve emailinizi doğru giriniz.")
            return

        self.status_label.setText("Bilgiler alınıyor...")

        # Sürücüyü başlatma
        try:
            driver = initialize_driver()
            wait = WebDriverWait(driver, 10)

            # Giriş yapma
            login(driver, wait, url, username, password)

            # Notlar sayfasına gitme
            reach_to_grades_page(driver, wait)

            # Öğrenci notlarını çekme
            student_grades = fetch_student_grades(driver, wait)

            # XML dosyasına kaydetme
            save_to_xml(student_grades)

            self.status_label.setText("Bilgiler alındı.")

        except Exception as e:
            self.status_label.setText(f"Bir hata oluştu: {str(e)}")

        finally:
            # Sürücüyü kapatma
            close_driver(driver)

def initialize_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")  # İşletim sistemi güvenlik modelini atla
    chrome_options.add_argument("--disable-dev-shm-usage")  # Sınırlı kaynak sorunlarını aş
    chrome_options.add_argument("--headless")  # Arayüz gereksinimi olmayan başsız modda çalıştır
    return webdriver.Chrome(options=chrome_options)

def login(driver, wait, url, username, password):
    try:
        driver.get(url)
        edevlet_button = wait.until(EC.element_to_be_clickable((By.ID, 'btnEdevletLogin')))
        edevlet_button.click()
        edevlet_username = wait.until(EC.element_to_be_clickable((By.ID, 'tridField')))
        edevlet_password = wait.until(EC.element_to_be_clickable((By.ID, 'egpField')))
        edevlet_username.send_keys(username)
        edevlet_password.send_keys(password)
        edevlet_signin = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "btn-send")))
        edevlet_signin.click()
    except TimeoutException:
        raise RuntimeError("Giriş yaparken zaman aşımı oldu. Lütfen tekrar deneyin.")
    except Exception as e:
        raise RuntimeError(f"Giriş yaparken bir hata oluştu: {str(e)}")

def reach_to_grades_page(driver, wait):
    try:
        side_bar = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "nav-link")))
        side_bar.click()
        lesson_info = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="proMenu"]/li[3]/a')))
        lesson_info.click()
        not_list_element = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="proMenu"]/li[3]/ul/li[3]/a')))
        not_list_element.click()
    except TimeoutException:
        raise RuntimeError("Notlar sayfasına ulaşırken zaman aşımı oldu. Lütfen tekrar deneyin.")
    except Exception as e:
        raise RuntimeError(f"Notlar sayfasına ulaşırken bir hata oluştu: {str(e)}")

def fetch_student_grades(driver, wait):
    try:
        iframe = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="IFRAME1"]')))
        driver.switch_to.frame(iframe)

        class_grades = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="grd_not_listesi"]')))
        grades_html = class_grades.get_attribute("outerHTML")

        # BeautifulSoup ile HTML'i işle
        soup = BeautifulSoup(grades_html, 'html.parser')

        # İlk satır dışındaki tüm satırları bul
        rows = soup.select('tr:not(:first-child)')

        # XML yapısı oluştur
        root = Element("grades")

        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 7:  # Yeterli hücremiz olduğundan emin ol
                class_code = cells[1].text.strip()
                class_name = cells[2].text.strip()
                situation = cells[3].text.strip()
                exam_grade = cells[4].text.strip()
                avg = cells[5].text.strip()
                grade = cells[6].text.strip()
                letter_grade = cells[7].text.strip()

                # Her satır için yeni bir 'class' öğesi oluştur
                class_element = SubElement(root, "class")
                class_element.set("id", class_code)

                # Sınıf bilgisi için alt öğeleri ekle
                SubElement(class_element, "class_code").text = class_code
                SubElement(class_element, "class_name").text = class_name
                SubElement(class_element, "situation").text = situation
                SubElement(class_element, "exam_grade").text = exam_grade
                SubElement(class_element, "avg").text = avg
                SubElement(class_element, "grade").text = grade
                SubElement(class_element, "letter_grade").text = letter_grade

        # Ayrıştırılan veriyi döndür
        return root
    except TimeoutException:
        raise RuntimeError("Not bilgilerini çekerken zaman aşımı oldu. Lütfen tekrar deneyin.")
    except Exception as e:
        raise RuntimeError(f"Not bilgilerini çekerken bir hata oluştu: {str(e)}")

def save_to_xml(root):
    # XML ağacı oluştur ve dosyaya kaydet
    tree = ElementTree(root)
    tree.write("student_grades.xml", encoding="utf-8", xml_declaration=True)

def close_driver(driver):
    driver.quit()

def main():
    app = QApplication(sys.argv)
    window = WebScraperApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
