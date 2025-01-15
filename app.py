from flask import Flask, request, jsonify, render_template, send_file, Response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import os
import time
from datetime import datetime

app = Flask(__name__)

# Global variables
driver = None
tenders = []
excel_filename = ""
keywords = []
start_date = None
progress_messages = []  # Store progress messages

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/load-keywords', methods=['POST'])
def load_keywords():
    global keywords
    if 'file' in request.files:
        file = request.files['file']
        keywords = [line.strip() for line in file.read().decode('utf-8').splitlines()]
    else:
        keywords = request.form['keywords'].split(',')
    return jsonify({"keywords": keywords})

@app.route('/set-start-date', methods=['POST'])
def set_start_date():
    global start_date
    start_date_input = request.form['start_date']
    try:
        start_date = datetime.strptime(start_date_input, "%Y-%m-%d")
        return jsonify({"status": "success", "start_date": start_date.strftime("%Y-%m-%d")})
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format"})

@app.route('/get-captcha', methods=['GET'])
def get_captcha():
    global driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page")
    time.sleep(3)
    captcha_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "captchaImage"))
    )
    captcha_base64 = captcha_element.get_attribute("src").split(",")[1]
    return jsonify({"captcha": captcha_base64})

@app.route('/refresh-captcha', methods=['GET'])
def refresh_captcha():
    global driver
    try:
        refresh_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "captcha"))
        )
        refresh_button.click()
        time.sleep(3)
        captcha_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "captchaImage"))
        )
        captcha_base64 = captcha_element.get_attribute("src").split(",")[1]
        return jsonify({"captcha": captcha_base64})
    except Exception as e:
        return jsonify({"error": f"Failed to refresh CAPTCHA: {str(e)}"}), 500

@app.route('/submit-captcha', methods=['POST'])
def submit_captcha():
    global driver, excel_filename, tenders
    captcha_text = request.form['captcha']
    try:
        captcha_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "captchaText"))
        )
        captcha_field.clear()
        captcha_field.send_keys(captcha_text)

        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "Submit"))
        )
        submit_button.click()
        time.sleep(5)

        # Start scraping tenders
        tenders = scrape_tenders()
        excel_filename = save_to_excel(tenders)

        if excel_filename:
            return jsonify({"status": "scraping_completed", "excel_filename": excel_filename})
        elif not tenders:
            return jsonify({"status": "no_data_found"})
        else:
            return jsonify({"status": "error", "message": "Unexpected issue occurred."})
    except Exception as e:
        return jsonify({"error": f"Failed to submit CAPTCHA: {str(e)}"}), 500

@app.route('/progress')
def progress():
    def generate():
        for message in progress_messages:
            yield f"data: {message}\n\n"
            time.sleep(1)  # Optional: Simulate a delay
    return Response(generate(), mimetype='text/event-stream')

def scrape_tenders():
    global driver, keywords, start_date
    tenders = []
    try:
        while True:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="table"]/tbody'))
            )
            table_body = driver.find_element(By.XPATH, '//*[@id="table"]/tbody')
            rows = table_body.find_elements(By.TAG_NAME, "tr")
            progress_messages.append(f"Found {len(rows) - 1} rows on this page.")
            for row in rows[1:]:
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) >= 7:
                    s_no = columns[0].text.strip()
                    published_date_str = columns[1].text.strip()
                    closing_date = columns[2].text.strip()
                    opening_date = columns[3].text.strip()
                    tender_title = columns[4].text.strip()
                    tender_link = columns[4].find_element(By.TAG_NAME, "a").get_attribute("href") if columns[4].find_elements(By.TAG_NAME, "a") else "No Link"
                    organisation_chain = columns[5].text.strip()
                    tender_value = columns[6].text.strip()

                    try:
                        published_date = datetime.strptime(published_date_str, "%d-%b-%Y %I:%M %p")
                    except ValueError:
                        continue

                    if published_date < start_date:
                        return tenders

                    if any(kw.lower() in tender_title.lower() for kw in keywords):
                        tenders.append({
                            "S.No": s_no,
                            "Published Date": published_date_str,
                            "Closing Date": closing_date,
                            "Opening Date": opening_date,
                            "Title": tender_title,
                            "Link": tender_link,
                            "Organisation Chain": organisation_chain,
                            "Tender Value": tender_value
                        })

            try:
                next_button = driver.find_element(By.ID, "loadNext")
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                progress_messages.append("Navigating to the next page...")
                next_button.click()
                time.sleep(5)
            except Exception:
                progress_messages.append("No more pages to scrape.")
                break
    finally:
        driver.quit()
    return tenders

def save_to_excel(tenders):
    if tenders:
        filename = f"tenders_GEM-CPP{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
        df = pd.DataFrame(tenders)
        df.to_excel(filename, index=False, engine='openpyxl')
        return filename
    return None

@app.route('/download-excel', methods=['GET'])
def download_excel():
    return send_file(excel_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
