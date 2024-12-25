import os
import time
import pandas as pd
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

options = Options()
options.binary_location = "/app/.apt/opt/google/chrome/chrome"  # Path to Chrome binary
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# Specify the Chromedriver path
service = Service("/app/.chromedriver/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)



# Flask app setup
app = Flask(__name__)

# Global variables for Selenium and scraping
tenders = []
csv_filename = ""
start_date = None
keywords = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/load-keywords', methods=['POST'])
def load_keywords():
    global keywords
    if 'file' in request.files and request.files['file']:
        file = request.files['file']
        keywords = [line.strip() for line in file.read().decode('utf-8').splitlines() if line.strip()]
    elif 'keywords' in request.form:
        keywords = [kw.strip() for kw in request.form['keywords'].split(',') if kw.strip()]
    else:
        return jsonify({"status": "error", "message": "No keywords provided"}), 400
    return jsonify({"keywords": keywords})

@app.route('/set-start-date', methods=['POST'])
def set_start_date():
    global start_date
    start_date_input = request.form['start_date']
    try:
        start_date = datetime.strptime(start_date_input, "%Y-%m-%d")
        return jsonify({"status": "success", "start_date": start_date_input})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format"})

@app.route('/get-captcha', methods=['GET'])
def get_captcha():
    global driver
    # Initialize WebDriver
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Navigate to the target website
    driver.get("https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page")
    time.sleep(3)  # Allow page to load

    # Extract CAPTCHA image as Base64
    captcha_element = driver.find_element(By.ID, "captchaImage")
    captcha_base64 = captcha_element.get_attribute("src").split(",")[1]
    return jsonify({"captcha": captcha_base64})

@app.route('/submit-captcha', methods=['POST'])
def submit_captcha():
    global driver, tenders, csv_filename
    captcha_text = request.form['captcha']

    # Fill CAPTCHA input field
    captcha_field = driver.find_element(By.ID, "captchaText")
    captcha_field.clear()
    captcha_field.send_keys(captcha_text)

    # Click the submit button
    submit_button = driver.find_element(By.ID, "Submit")
    submit_button.click()
    time.sleep(5)  # Wait for the page to load

    # Start scraping
    tenders = scrape_tenders()
    if tenders:
        csv_filename = save_to_excel(tenders)  # Save as Excel file
        return jsonify({"status": "scraping_completed", "csv_filename": csv_filename})
    else:
        return jsonify({"status": "no_data_found"})

@app.route('/debug-chrome')
def debug_chrome():
    import subprocess
    try:
        chrome_version = subprocess.check_output(["/app/.apt/usr/bin/google-chrome", "--version"]).decode("utf-8")
        return f"Google Chrome version: {chrome_version}"
    except Exception as e:
        return f"Error: {str(e)}"


def scrape_tenders():
    global driver, start_date, keywords
    tenders = []
    try:
        while True:
            # Wait for the table to load
            table_body = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="table"]/tbody'))
            )
            rows = table_body.find_elements(By.TAG_NAME, "tr")

            for row in rows[1:]:  # Skip the header row
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) >= 7:
                    tender_details = {
                        "S.No": columns[0].text.strip(),
                        "Published Date": columns[1].text.strip(),
                        "Closing Date": columns[2].text.strip(),
                        "Opening Date": columns[3].text.strip(),
                        "Title": columns[4].text.strip(),
                        "Link": columns[4].find_element(By.TAG_NAME, "a").get_attribute("href"),
                        "Organisation Chain": columns[5].text.strip(),
                        "Tender Value": columns[6].text.strip(),
                    }
                    # Convert and filter by start_date
                    try:
                        published_date = datetime.strptime(tender_details["Published Date"], "%d-%b-%Y %I:%M %p")
                        if published_date < start_date:
                            return tenders  # Stop scraping
                    except ValueError:
                        continue

                    # Keyword matching
                    if any(kw.lower() in tender_details["Title"].lower() for kw in keywords):
                        tenders.append(tender_details)

            # Navigate to the next page
            try:
                next_button = driver.find_element(By.ID, "loadNext")
                next_button.click()
                time.sleep(10)
            except Exception:
                break
    finally:
        driver.quit()
    return tenders

def save_to_excel(tenders):
    global start_date
    filename = f"tenders_{start_date.strftime('%Y-%m-%d')}.xlsx"
    df = pd.DataFrame(tenders)
    df.to_excel(filename, index=False, engine='openpyxl')
    return filename

@app.route('/download-file', methods=['GET'])
def download_file():
    filename = request.args.get('filename')
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    else:
        return jsonify({"status": "error", "message": "File not found"}), 404


if __name__ == '__main__':
    app.run(debug=True)
