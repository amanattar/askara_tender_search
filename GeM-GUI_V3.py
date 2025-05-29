import sys
import os
import time
import pandas as pd
from datetime import datetime
import re

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QDateEdit, QPushButton, QTextEdit, QLineEdit
)
from PyQt6.QtCore import QThread, pyqtSignal, QDate

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# New imports for webdriver_manager and BeautifulSoup
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

BASE_KEYWORDS = [
    "hose", "hoses",
    "pdc bit", "pdc bits", "bit" "bits"
    "gate valve", "gate valves", "gate-valve", "gate-valves",
    "ball valve", "ball valves", "ball-valve", "ball-valves",
    "check valve", "check valves", "check-valve", "check-valves",
    "choke", "chokes",
    "well head", "well heads", "well-head", "well-heads",
    "well test equipment", "well-test equipment", "well test equipments", "well-test equipments",
    "christmas tree", "xmas tree", "x-mas tree", "christmas-tree", "x-mas-tree", "x-mas", "christmas", "xmas", 
    "bop",
    "blowout preventer", "blowout preventers", "blow-out preventer", "blow-out preventers", "blowout-preventer",
    "manifold", "manifolds",
    "well contain", "well contains", "well-contain", "well-contains",
    "onshore", "on shore", "on-shore",
    "offshore", "off shore", "off-shore",
    "subsea application", "subsea applications", "subsea-application", "subsea-applications",
    "hi-lo safety valve", "hi-lo safety valves", "hi lo safety valve", "hi lo safety valves", "hi-lo-safety-valve", "hi-lo-safety-valves",
    "charter hire rig", "charter hire rigs", "charter-hire rig", "charter-hire rigs",
    "remote monitoring", "remote-monitoring", "remote monitor", "remote-monitor",
    "realtime monitoring", "real-time monitoring", "real time monitoring", "realtime-monitoring", "real-time-monitoring",
    "well stimulation", "well-stimulation", "well stimulations", "well-stimulations",
    "acidizing", "acidising",
    "hf / hcl", "hf/hcl", "hydrofluoric acid / hydrochloric acid", "hydrofluoric acid/hydrochloric acid", "hf & hcl", "hf and hcl",
    "mopu",
    "engineering services", "engineering-services",
    "lost circulation control additive", "lost circulation control additives", "lost-circulation-control additive", "lost-circulation-control additives",
    "lcca",
    "cement additive", "cement additives", "cement-additive", "cement-additives",
    "downhole gauge", "downhole gauges", "downhole-gauge", "downhole-gauges",
    "tubing encapsulated cable", "tubing encapsulated cables", "tubing-encapsulated cable", "tubing-encapsulated cables", "tec", "t.e.c.",
    "control line", "control lines", "control-line", "control-lines",
    "drone", "drones",
    "piper", "pipers",
    "free floating piper", "free floating pipers", "free-floating piper", "free-floating pipers",
    "carbon mapping", "carbon-mapping",
    "carbon footprint", "carbon footprints", "carbon-footprint", "carbon-footprints",
    "ccus", "carbon capture utilization and storage", "carbon capture, utilization and storage",
    "live rig monitoring", "live-rig monitoring", "live rig-monitoring", "live-rig-monitoring",
    "analytics", "analytic",
    "production testing service", "production testing services", "production-testing-service", "production-testing-services",
    "heavy weight drill pipe", "heavy weight drill pipes", "heavy-weight drill pipe", "heavy-weight drill pipes", "heavyweight drill pipe", "heavyweight drill pipes",
    "drill collar", "drill collars", "drill-collar", "drill-collars",
    "enhanced oil recovery", "enhanced-oil recovery", "eor",
    "esp", "electric submersible pump", "electric submersible pumps", "electric-submersible pump", "electric-submersible pumps"
]

class ScraperThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, organization, start_date, end_date, keywords_str, parent=None):
        super().__init__(parent)
        self.organization = organization
        self.start_date   = start_date
        self.end_date     = end_date
        self.search_keywords = False

        # parse anything the user typed
        user_kw = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]

        if user_kw:
            self.keywords = user_kw  # Only user-defined
            self.log_signal.emit("Using only user-defined keywords.")
            self.search_keywords = True
        else:
            self.keywords = BASE_KEYWORDS  # Use full base list
            self.log_signal.emit("No keywords entered. Using full predefined list.")

    def normalize(self, text):
        import re
        return re.sub(r'\W+', ' ', text.lower()).strip()


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

            # Use webdriver_manager to automatically download and manage ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

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

            tender_list = []
            tender_list_filtered = []
            page_num = 1

            while True:
                self.log_signal.emit(f"Extracting data from Page {page_num}...")
                try:
                    wait.until(EC.presence_of_element_located((By.ID, "result")))
                    self.log_signal.emit("Results loaded successfully!")
                except TimeoutException:
                    self.log_signal.emit("Initial load failed. Retrying once after 5s...")
                    time.sleep(5)
                    driver.refresh()
                    try:
                        time.sleep(5)
                        wait.until(EC.presence_of_element_located((By.ID, "result")))
                        self.log_signal.emit("Results loaded successfully on retry!")
                    except:
                        self.log_signal.emit("Results section did not load after retry.")
                        driver.quit()
                        self.finished_signal.emit()
                        return

                    # ─── Selenium-based extraction ────────────────────────────────────
                tender_elems = driver.find_elements(By.CSS_SELECTOR, "#bidCard .card")
                self.log_signal.emit(f"Found {len(tender_elems)} tenders on Page {page_num} (using Selenium)!") 

                for card_el in tender_elems:
                    # 1) BID No & Link
                    try:
                        link_el = card_el.find_element(By.CSS_SELECTOR, ".bid_no a")
                        bid_no   = link_el.text
                        bid_link = link_el.get_attribute("href")
                    except:
                        bid_no, bid_link = "N/A", "N/A"

                    # 2) Item Description (first try data-content, then fallback to "Items:" row)
                    item_desc_full = "N/A"
                    raw_html = card_el.get_attribute("outerHTML")

                    # Primary: Try to extract from data-content
                    marker = 'data-content="'
                    start = raw_html.find(marker)
                    if start != -1:
                        start += len(marker)
                        end = raw_html.find('">', start)
                        if end != -1:
                            item_desc_full = raw_html[start:end]
                        else:
                            item_desc_full = raw_html[start:]
                            # self.log_signal.emit(f"⚠️ Unclosed data-content for BID: {bid_no}")
                    else:
                        # self.log_signal.emit(f"⚠️ No data-content found for BID: {bid_no}. Trying fallback...")

                        # Fallback: Try to extract from text near 'Items:'
                        try:
                            item_rows = card_el.find_elements(By.CSS_SELECTOR, ".col-md-4 .row")
                            for row in item_rows:
                                text = row.text.strip()
                                if text.lower().startswith("items:"):
                                    item_desc_full = text.split(":", 1)[1].strip()
                                    # self.log_signal.emit(f"✅ Fallback item description found: {item_desc_full} (BID: {bid_no})")
                                    break
                        except Exception as e:
                            self.log_signal.emit(f"❌ Failed fallback extraction for BID: {bid_no}: {str(e)}")

                    # Log if still N/A
                    if item_desc_full == "N/A":
                        # self.log_signal.emit(f"❗ Item description is still N/A. BID: {bid_no}")
                        with open(f"debug_card_{bid_no.replace('/', '_')}.html", "w", encoding="utf-8") as f:
                            f.write(raw_html)


                    # 3) Quantity
                    try:
                        qty_el = card_el.find_element(By.CSS_SELECTOR, ".col-md-4 div.row:nth-of-type(2)")
                        quantity = qty_el.text.split(":",1)[1].strip()
                    except:
                        quantity = "N/A"

                    # 4) Department
                    try:
                        dept_el = card_el.find_element(By.CSS_SELECTOR, ".col-md-5 div.row")
                        department = dept_el.text.replace("\n"," ")
                    except:
                        department = "N/A"

                    # 5) Start / End Dates
                    try:
                        start_el = card_el.find_element(By.CSS_SELECTOR, ".start_date")
                        start_date_text = start_el.text
                    except:
                        start_date_text = "N/A"
                    try:
                        end_el = card_el.find_element(By.CSS_SELECTOR, ".end_date")
                        end_date_text = end_el.text
                    except:
                        end_date_text = "N/A"

                    # Store all tenders first
                    tender_list.append({
                        "BID NO": bid_no,
                        "Link": bid_link,
                        "Item Description": item_desc_full,
                        "Quantity": quantity,
                        "Department": department,
                        "Start Date": start_date_text,
                        "End Date": end_date_text,
                        "Page": page_num
                    })


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

            # Prepare file saving
            today_str = datetime.today().strftime("%Y-%m-%d")
            org_short = self.organization.replace(" ", "_").lower()
            if getattr(sys, 'frozen', False):
                app_path = os.path.dirname(sys.executable)
            else:
                app_path = os.path.dirname(os.path.abspath(__file__))

            self.log_signal.emit("Applying keyword filtering to all collected tenders...")

            for tender in tender_list:
                desc_clean = self.normalize(tender["Item Description"])
                matched_kw = None
                for kw in self.keywords:
                    if self.normalize(kw) in desc_clean:
                        matched_kw = kw
                        break
                if matched_kw:
                    tender_copy = tender.copy()
                    tender_copy["Matched Keyword"] = matched_kw
                    tender_list_filtered.append(tender_copy)

            self.log_signal.emit(f"Total tenders scraped: {len(tender_list)}")
            self.log_signal.emit(f"Tenders matched by keywords: {len(tender_list_filtered)}")

            if self.search_keywords:  # user provided custom keyword
                filename = os.path.join(app_path, f"{today_str}-{org_short}-search.xlsx")
            else:
                filename = os.path.join(app_path, f"{today_str}-{org_short}-filtered.xlsx")

    
            # filename = os.path.join(app_path, f"{today_str}-{org_short}-filtered.xlsx")
            filename1 = os.path.join(app_path, f"{today_str}-{org_short}-all.xlsx")
            df = pd.DataFrame(tender_list_filtered)
            df.drop_duplicates(subset=["BID NO"], inplace=True)
            df.reset_index(drop=True, inplace=True)
            df.to_excel(filename, index=False)
            self.log_signal.emit(f"Filtered tender data saved to '{filename}'")
            df_all = pd.DataFrame(tender_list)
            df_all.to_excel(filename1, index=False)
            self.log_signal.emit(f"All tender data saved to '{filename1}'")
            self.log_signal.emit("Scraping completed successfully!")
            driver.quit()

        except Exception as e:
            self.log_signal.emit(f"An error occurred: {str(e)}")
        self.finished_signal.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tender Scraper")
        self.setMinimumSize(600, 500)  # Increased minimum height to accommodate keyword input
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
        start_label = QLabel("Bid End Date (From):")
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setDate(QDate.currentDate())
        end_label = QLabel("Bid End Date (To)")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date_edit)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date_edit)
        layout.addLayout(date_layout)

        # Keyword input
        keyword_layout = QHBoxLayout()
        keyword_label = QLabel("Keywords (comma-separated):")
        self.keyword_input = QLineEdit()
        keyword_layout.addWidget(keyword_label)
        keyword_layout.addWidget(self.keyword_input)
        layout.addLayout(keyword_layout)

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
        keywords_str = self.keyword_input.text()

        self.append_log(f"Selected Organization: {organization}")
        self.append_log(f"Selected Date Range: {start_date} to {end_date}")
        self.append_log(f"Keywords: {keywords_str}")
        self.start_button.setEnabled(False)

        self.worker = ScraperThread(organization, start_date, end_date, keywords_str)
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