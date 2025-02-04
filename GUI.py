import sys
import os
import time
import threading
import base64
import pandas as pd

from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit, QMessageBox,
    QDateEdit
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QObject, QByteArray
from PyQt6.QtGui import QPixmap

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ScraperSignals(QObject):
    """Signals emitted by the scraper worker thread."""
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    results_saved = pyqtSignal(str)
    captcha_image = pyqtSignal(bytes)   # Emit raw bytes of the CAPTCHA screenshot

class ScraperThread(threading.Thread):
    """
    Worker thread to perform the web scraping so the UI remains responsive.
    This thread will emit signals back to the main GUI to update logs, captcha image, etc.
    """
    def __init__(self, url, start_date, keywords, signals):
        super().__init__()
        self.url = url
        self.start_date = start_date
        self.keywords = keywords
        self.signals = signals
        self.driver = None
        self.tenders = []
        self.captcha_text = None      # Will be set by GUI
        self.captcha_ready_event = threading.Event()  # Signaled by GUI when user enters CAPTCHA

    def run(self):
        """Main worker function for scraping."""
        try:
            self.scrape_tenders()
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            if self.driver:
                self.driver.quit()
            self.signals.finished.emit()

    def log(self, msg):
        """Helper method to emit log messages."""
        self.signals.log.emit(msg)

    def scrape_tenders(self):
        # Extract domain name from the URL for CSV naming
        domain = self.url.split("//")[-1].split("/")[0]
        csv_filename = f"{domain}_{self.start_date.strftime('%Y-%m-%d')}.csv"

        # Setup Selenium WebDriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install())
        )

        self.log("Navigating to the page...")
        self.driver.get(self.url)
        time.sleep(5)  # Allow the page to load
        self.log("Website loaded in Chrome.")

        # ---------------------------------------------------------------------
        # 1. Locate CAPTCHA IMAGE using the selector "#captchaImage"
        try:
            captcha_img = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#captchaImage"))
            )
        except Exception:
            self.log("No CAPTCHA image found or timed out waiting. Proceeding without CAPTCHA.")
            captcha_img = None

        if captcha_img:
            # Take a screenshot of just the CAPTCHA element as bytes (PNG)
            captcha_bytes = captcha_img.screenshot_as_png
            # Emit the raw bytes to the GUI
            self.signals.captcha_image.emit(captcha_bytes)

            self.log("Waiting for user to input CAPTCHA text in the GUI...")
            # Wait for the user to set self.captcha_text and signal that it's ready
            self.captcha_ready_event.wait()  # Blocking wait

            if self.captcha_text:
                # Locate the CAPTCHA input field using its id "captchaText"
                captcha_input = self.driver.find_element(By.CSS_SELECTOR, "input#captchaText")
                captcha_input.clear()
                captcha_input.send_keys(self.captcha_text)

                try:
                    # Locate and click the submit button using its id "Submit"
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, "input#Submit")
                    submit_button.click()
                    self.log("Search submit button clicked. Waiting 10 seconds for page refresh...")
                    time.sleep(10)  # Wait for the page to refresh
                except Exception as e:
                    self.log("Could not locate or click the submit button: " + str(e))
            else:
                self.log("No CAPTCHA text provided. Proceeding...")

        # ---------------------------------------------------------------------
        # Now proceed with scraping the table data.
        self.log("Starting table extraction...")

        while True:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="table"]/tbody'))
            )
            table_body = self.driver.find_element(By.XPATH, '//*[@id="table"]/tbody')
            rows = table_body.find_elements(By.TAG_NAME, "tr")
            self.log(f"Found {len(rows)} rows on this page.")

            stop_scraping = False

            for row in rows[1:]:  # Skip header row
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) >= 7:
                    s_no = columns[0].text.strip()
                    published_date_str = columns[1].text.strip()
                    closing_date = columns[2].text.strip()
                    opening_date = columns[3].text.strip()
                    tender_title = columns[4].text.strip()
                    try:
                        tender_link = columns[4].find_element(By.TAG_NAME, "a").get_attribute("href")
                    except Exception:
                        tender_link = "No Link"
                    organisation_chain = columns[5].text.strip()
                    tender_value = columns[6].text.strip()

                    try:
                        published_date = datetime.strptime(published_date_str, "%d-%b-%Y %I:%M %p")
                    except ValueError as e:
                        self.log(f"Date parsing error: {e}, skipping row.")
                        continue

                    if published_date < self.start_date:
                        self.log(f"Published date {published_date_str} < start date. Stopping.")
                        stop_scraping = True
                        break

                    matched = any(kw.lower() in tender_title.lower() for kw in self.keywords)
                    if matched:
                        self.tenders.append({
                            "S.No": s_no,
                            "Published Date": published_date_str,
                            "Closing Date": closing_date,
                            "Opening Date": opening_date,
                            "Title": tender_title,
                            "Link": tender_link,
                            "Organisation Chain": organisation_chain,
                            "Tender Value": tender_value
                        })

            if stop_scraping:
                break

            try:
                next_button = self.driver.find_element(By.ID, "loadNext")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                next_button.click()
                time.sleep(5)
            except Exception as e:
                self.log(f"No Next button found or clickable: {e}")
                break

        if self.tenders:
            df = pd.DataFrame(self.tenders)
            df.to_csv(csv_filename, index=False)
            self.log(f"Scraping completed! Results saved to '{csv_filename}'.")
            self.signals.results_saved.emit(csv_filename)
        else:
            self.log("No matching tenders found.")
            self.signals.results_saved.emit("")

class ScraperGUI(QMainWindow):
    """Main Window for the PyQt6 Web Scraping Application with CAPTCHA handling."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tender Scraper (PyQt6)")

        self.url = "https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page"
        self.keywords = []
        self.start_date = None

        container = QWidget()
        main_layout = QVBoxLayout()

        # Keywords Section
        kw_layout = QHBoxLayout()
        self.kw_label = QLabel("Keywords (comma-separated):")
        self.kw_input = QLineEdit()
        self.kw_button_file = QPushButton("Load from File")
        self.kw_button_file.clicked.connect(self.load_keywords_file)
        kw_layout.addWidget(self.kw_label)
        kw_layout.addWidget(self.kw_input)
        kw_layout.addWidget(self.kw_button_file)
        main_layout.addLayout(kw_layout)

        # Start Date Section
        date_layout = QHBoxLayout()
        self.date_label = QLabel("Start Date:")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_label)
        date_layout.addWidget(self.date_edit)
        main_layout.addLayout(date_layout)

        # Start Scraping Button
        self.start_button = QPushButton("Start Scraping")
        self.start_button.clicked.connect(self.start_scraping)
        main_layout.addWidget(self.start_button)

        # CAPTCHA Display and Input
        captcha_box = QHBoxLayout()
        self.captcha_label = QLabel("CAPTCHA Image:")
        self.captcha_image_label = QLabel()
        self.captcha_image_label.setFixedSize(200, 80)
        self.captcha_image_label.setStyleSheet("border: 1px solid black;")
        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText("Enter CAPTCHA here...")
        self.captcha_submit_btn = QPushButton("Submit CAPTCHA")
        self.captcha_submit_btn.clicked.connect(self.submit_captcha)
        captcha_box.addWidget(self.captcha_label)
        captcha_box.addWidget(self.captcha_image_label)
        captcha_box.addWidget(self.captcha_input)
        captcha_box.addWidget(self.captcha_submit_btn)
        main_layout.addLayout(captcha_box)

        # Log Output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.log_output)

        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.scraper_thread = None
        self.scraper_signals = None

    def load_keywords_file(self):
        """Load keywords from a file."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select Keywords File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_keywords = [line.strip() for line in f if line.strip()]
                current_text = self.kw_input.text().strip()
                if current_text:
                    existing_list = [kw.strip() for kw in current_text.split(",") if kw.strip()]
                    all_keywords = existing_list + file_keywords
                else:
                    all_keywords = file_keywords
                self.kw_input.setText(", ".join(all_keywords))
                self.log_message(f"Loaded {len(file_keywords)} keywords from file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file: {e}")

    def start_scraping(self):
        """Prepare data and launch the scraper in a separate thread."""
        text = self.kw_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Warning", "Please provide keywords before starting.")
            return
        self.keywords = [kw.strip() for kw in text.split(",") if kw.strip()]

        qt_date = self.date_edit.date()
        date_str = qt_date.toString("yyyy-MM-dd")
        try:
            self.start_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            QMessageBox.warning(self, "Warning", "Invalid start date.")
            return

        self.start_button.setEnabled(False)
        self.log_output.clear()
        self.log_message("Starting the scraping process... Chrome will open shortly.")

        self.scraper_signals = ScraperSignals()
        self.scraper_signals.log.connect(self.log_message)
        self.scraper_signals.finished.connect(self.scraping_finished)
        self.scraper_signals.error.connect(self.scraping_error)
        self.scraper_signals.results_saved.connect(self.scraping_results_saved)
        self.scraper_signals.captcha_image.connect(self.display_captcha)

        self.scraper_thread = ScraperThread(self.url, self.start_date, self.keywords, self.scraper_signals)
        self.scraper_thread.start()

    def display_captcha(self, img_bytes: bytes):
        """Display the CAPTCHA image in the GUI."""
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes, "PNG")
        scaled_pix = pixmap.scaled(
            self.captcha_image_label.width(),
            self.captcha_image_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.captcha_image_label.setPixmap(scaled_pix)
        self.log_message("CAPTCHA image displayed. Please enter CAPTCHA text and click 'Submit CAPTCHA'.")

    def submit_captcha(self):
        """Handle CAPTCHA submission from the GUI."""
        captcha_text = self.captcha_input.text().strip()
        if not captcha_text:
            QMessageBox.warning(self, "Warning", "CAPTCHA text cannot be empty.")
            return

        if self.scraper_thread and self.scraper_thread.is_alive():
            self.scraper_thread.captcha_text = captcha_text
            self.scraper_thread.captcha_ready_event.set()  # Unblock the scraper thread
            self.log_message("CAPTCHA text submitted to the scraper thread.")

        self.captcha_input.setEnabled(False)
        self.captcha_submit_btn.setEnabled(False)

    def scraping_finished(self):
        """Callback when scraping thread finishes."""
        self.log_message("Scraping thread finished.")
        self.start_button.setEnabled(True)
        self.captcha_input.setEnabled(True)
        self.captcha_submit_btn.setEnabled(True)

    def scraping_error(self, error_message):
        QMessageBox.critical(self, "Scraping Error", f"An error occurred: {error_message}")

    def scraping_results_saved(self, filename):
        if filename:
            QMessageBox.information(self, "Scraping Completed", f"Results saved to '{filename}'.")
        else:
            QMessageBox.information(self, "No Results", "No matching tenders found.")

    def log_message(self, msg):
        self.log_output.append(msg)
        print(msg)

def main():
    app = QApplication(sys.argv)
    gui = ScraperGUI()
    gui.resize(900, 600)
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
