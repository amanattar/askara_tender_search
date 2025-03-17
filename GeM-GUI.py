import sys
import os
import time
import pandas as pd
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QDateEdit, QPushButton, QTextEdit
)
from PyQt6.QtCore import QThread, pyqtSignal, QDate

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ScraperThread(QThread):
    # Signal to update log text in the UI
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, organization, start_date, end_date, parent=None):
        super().__init__(parent)
        self.organization = organization
        self.start_date = start_date
        self.end_date = end_date

    def run(self):
        try:
            self.log_signal.emit("Starting scraper...")
            # Set up Selenium WebDriver in Headless Mode
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920x1080")
            driver = webdriver.Chrome(options=options)

            # Open the GeM website
            url = "https://bidplus.gem.gov.in/advance-search"
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            self.log_signal.emit("Opened GeM website.")

            # Click "Search by Ministry / Organization" tab
            ministry_tab = wait.until(EC.element_to_be_clickable((By.ID, "ministry-tab")))
            ministry_tab.click()
            time.sleep(2)

            # Select "MINISTRY OF PETROLEUM AND NATURAL GAS"
            ministry_dropdown = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//select[@id='ministry']/following-sibling::span")
            ))
            ministry_dropdown.click()
            time.sleep(1)
            ministry_option = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//li[contains(text(), 'MINISTRY OF PETROLEUM AND NATURAL GAS')]")
            ))
            ministry_option.click()

            # Select the Organization based on user selection
            organization_dropdown = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//select[@id='organization']/following-sibling::span")
            ))
            organization_dropdown.click()
            time.sleep(1)
            organization_option = wait.until(EC.element_to_be_clickable(
                (By.XPATH, f"//li[contains(text(), '{self.organization}')]")
            ))
            organization_option.click()

            # Set the date range
            driver.execute_script("document.getElementById('bidendFromMinistrySearch').removeAttribute('readonly')")
            driver.execute_script("document.getElementById('bidendToMinistrySearch').removeAttribute('readonly')")
            time.sleep(1)

            from_date_elem = wait.until(EC.element_to_be_clickable((By.ID, "bidendFromMinistrySearch")))
            to_date_elem = wait.until(EC.element_to_be_clickable((By.ID, "bidendToMinistrySearch")))

            from_date_elem.clear()
            from_date_elem.send_keys(self.start_date)
            time.sleep(1)

            to_date_elem.clear()
            to_date_elem.send_keys(self.end_date)
            time.sleep(1)

            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)

            # Trigger the search button
            try:
                search_button = wait.until(EC.presence_of_element_located((By.ID, "searchByBid")))
                driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
                time.sleep(1)
                try:
                    driver.execute_script("searchBid('ministry-search')")
                    self.log_signal.emit("Search triggered successfully!")
                except Exception as e:
                    self.log_signal.emit(f"Search button trigger failed: {str(e)}")
            except Exception as e:
                self.log_signal.emit(f"Search button not found: {str(e)}")

            time.sleep(5)

            try:
                wait.until(EC.presence_of_element_located((By.ID, "result")))
                self.log_signal.emit("Results loaded successfully!")
            except:
                self.log_signal.emit("Results section did not load.")
                driver.quit()
                self.finished_signal.emit()
                return

            # Define keywords for filtering tenders
            keywords = [
                "hoses", "pdc bits", "gate valves", "ball valves", "check valves",
                "chokes", "well heads", "well test equipment", "christmas tree", "bop", "blowout preventer",
                "manifolds", "well contain", "onshore", "offshore", "subsea applications",
                "hi-lo safety valves", "charter hire rigs", "remote monitoring", "realtime monitoring", "well stimulation",
                "acidizing", "hf / hcl", "mopu", "engineering  services", "lost circulation control additive",
                "lcca", "cement additive", "downhole gauges", "tubing encapsulated cable", "control line",
                "drone", "pipers", "free floating pipers", "downhole gauges", "control line",
                "carbon mapping", "carbon footprint", "ccus", "live rig monitoring", "analytics",
                "production testing services", "heavy weight drill pipe", "drill collars", "enhanced oil recovery", "esp"
            ]
            tender_list = []
            page_num = 1

            while True:
                self.log_signal.emit(f"Extracting data from Page {page_num}...")
                try:
                    wait.until(EC.presence_of_element_located((By.ID, "result")))
                    self.log_signal.emit("Results section loaded successfully!")
                except:
                    self.log_signal.emit("Results section did not load.")
                    break

                tenders = driver.find_elements(By.CSS_SELECTOR, "#bidCard .card")
                self.log_signal.emit(f"Found {len(tenders)} tenders on Page {page_num}!")

                for tender in tenders:
                    try:
                        bid_no = tender.find_element(By.CSS_SELECTOR, ".bid_no a").text
                        bid_link = tender.find_element(By.CSS_SELECTOR, ".bid_no a").get_attribute("href")
                    except:
                        bid_no, bid_link = "N/A", "N/A"

                    try:
                        item_desc = tender.find_element(By.CSS_SELECTOR, ".col-md-4 a").get_attribute("data-content")
                    except:
                        item_desc = "N/A"

                    try:
                        quantity = tender.find_element(By.CSS_SELECTOR, ".col-md-4 div.row:nth-of-type(2)").text.split(":")[1].strip()
                    except:
                        quantity = "N/A"

                    try:
                        department = tender.find_element(By.CSS_SELECTOR, ".col-md-5 div.row").text.replace("\n", " ")
                    except:
                        department = "N/A"

                    try:
                        start_date_text = tender.find_element(By.CSS_SELECTOR, ".start_date").text
                    except:
                        start_date_text = "N/A"

                    try:
                        end_date_text = tender.find_element(By.CSS_SELECTOR, ".end_date").text
                    except:
                        end_date_text = "N/A"

                    item_desc_lower = item_desc.lower()
                    if any(keyword in item_desc_lower for keyword in keywords):
                        tender_list.append({
                            "BID NO": bid_no,
                            "Link": bid_link,
                            "Item Description": item_desc,
                            "Quantity": quantity,
                            "Department": department,
                            "Start Date": start_date_text,
                            "End Date": end_date_text,
                            "Page": page_num
                        })
                        self.log_signal.emit(f"Matched Tender: {bid_no} - {item_desc[:50]}...")

                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "a.page-link.next")
                    driver.execute_script("arguments[0].scrollIntoView();", next_button)
                    time.sleep(1)
                    next_button.click()
                    page_num += 1
                    time.sleep(3)
                except:
                    self.log_signal.emit("No more pages left. Exiting...")
                    break

            # Prepare file saving in the same directory as the .exe (or script)
            today_str = datetime.today().strftime("%Y-%m-%d")
            org_short = self.organization.replace(" ", "_").lower()
            if getattr(sys, 'frozen', False):
                app_path = os.path.dirname(sys.executable)
            else:
                app_path = os.path.dirname(os.path.abspath(__file__))
            filename = os.path.join(app_path, f"{today_str}-{org_short}.xlsx")

            df = pd.DataFrame(tender_list)
            df.to_excel(filename, index=False)
            self.log_signal.emit(f"Filtered tender data saved to '{filename}'")
            driver.quit()

        except Exception as e:
            self.log_signal.emit(f"An error occurred: {str(e)}")
        self.finished_signal.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tender Scraper")
        self.setMinimumSize(600, 400)
        self.init_ui()
        self.worker = None

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Organization selection
        org_layout = QHBoxLayout()
        org_label = QLabel("Select Organization:")
        self.org_combo = QComboBox()
        self.org_combo.addItems([
            "OIL AND NATURAL GAS CORPORATION LIMITED",
            "OIL INDIA LIMITED"
        ])
        org_layout.addWidget(org_label)
        org_layout.addWidget(self.org_combo)
        layout.addLayout(org_layout)

        # Date selection
        date_layout = QHBoxLayout()
        start_label = QLabel("Start Date:")
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setDate(QDate.currentDate())
        end_label = QLabel("End Date:")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date_edit)
        layout.addLayout(date_layout)

        # Start button
        self.start_button = QPushButton("Start Scraping")
        self.start_button.clicked.connect(self.start_scraping)
        layout.addWidget(self.start_button)

        # Log output (read-only)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def append_log(self, message):
        self.log_text.append(message)

    def start_scraping(self):
        organization = self.org_combo.currentText()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        self.append_log(f"Selected Organization: {organization}")
        self.append_log(f"Selected Date Range: {start_date} to {end_date}")
        self.start_button.setEnabled(False)

        self.worker = ScraperThread(organization, start_date, end_date)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.scraping_finished)
        self.worker.start()

    def scraping_finished(self):
        self.append_log("Scraping finished!")
        self.start_button.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
