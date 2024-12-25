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
from redis import Redis
from rq import Queue
from rq.job import Job
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Flask app setup
app = Flask(__name__)

# Redis connection and RQ queue
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "rediss://:pb210e95b44ffaf31347bc148147174d6c7b6496d87d9c41e5c10a5749b403712@ec2-18-211-255-108.compute-1.amazonaws.com:30100"))
queue = Queue(connection=redis_conn)

# Global variables for Selenium and scraping
tenders = []
csv_filename = ""
start_date = None
keywords = []

# WebDriver configuration
def create_webdriver():
    options = Options()
    options.binary_location = "/app/.chrome-for-testing/chrome-linux64/chrome"
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service("/app/.chrome-for-testing/chromedriver-linux64/chromedriver")
    return webdriver.Chrome(service=service, options=options)


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


@app.route('/submit-captcha', methods=['POST'])
def submit_captcha():
    captcha_text = request.form['captcha']
    job = queue.enqueue(scrape_tenders_task, captcha_text)
    return jsonify({"status": "submitted", "job_id": job.get_id()})


@app.route('/job-status/<job_id>', methods=['GET'])
def job_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        if job.is_finished:
            return jsonify({"status": "completed", "result": job.result})
        elif job.is_failed:
            return jsonify({"status": "failed"})
        else:
            return jsonify({"status": "in_progress"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


def scrape_tenders_task(captcha_text):
    global csv_filename
    tenders = []
    driver = create_webdriver()
    try:
        driver.get("https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page")
        time.sleep(3)

        # Fill CAPTCHA
        captcha_field = driver.find_element(By.ID, "captchaText")
        captcha_field.clear()
        captcha_field.send_keys(captcha_text)

        # Submit the CAPTCHA
        submit_button = driver.find_element(By.ID, "Submit")
        submit_button.click()
        time.sleep(5)

        # Scrape tenders
        tenders = scrape_tenders(driver)

        # Save results to Excel
        if tenders:
            csv_filename = save_to_excel(tenders)
    finally:
        driver.quit()
    return csv_filename


def scrape_tenders(driver):
    global start_date, keywords
    tenders = []
    try:
        while True:
            table_body = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="table"]/tbody'))
            )
            rows = table_body.find_elements(By.TAG_NAME, "tr")

            for row in rows[1:]:
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
                    try:
                        published_date = datetime.strptime(tender_details["Published Date"], "%d-%b-%Y %I:%M %p")
                        if published_date < start_date:
                            return tenders
                    except ValueError:
                        continue

                    if any(kw.lower() in tender_details["Title"].lower() for kw in keywords):
                        tenders.append(tender_details)

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
