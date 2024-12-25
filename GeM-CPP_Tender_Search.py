import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Function to load keywords
def load_keywords():
    print("How would you like to provide the keywords?")
    print("1. Provide a path to a 'keywords.txt' file.")
    print("2. Manually type keywords separated by commas.")
    
    choice = input("Enter 1 or 2: ").strip()
    
    if choice == "1":
        keyword_file = input("Enter the path to your 'keywords.txt' file: ").strip()
        if os.path.exists(keyword_file):
            try:
                with open(keyword_file, "r") as file:
                    keywords = [line.strip() for line in file.readlines() if line.strip()]
                    print(f"Loaded {len(keywords)} keywords from '{keyword_file}'.")
                    return keywords
            except Exception as e:
                print(f"Error reading file: {e}. Exiting.")
                exit()
        else:
            print("File not found. Exiting.")
            exit()
    elif choice == "2":
        keyword_input = input("Enter keywords separated by commas: ")
        keywords = [kw.strip() for kw in keyword_input.split(",") if kw.strip()]
        print(f"Loaded {len(keywords)} keywords from manual input.")
        return keywords
    else:
        print("Invalid choice. Exiting.")
        exit()

# Function to get start date
def get_start_date():
    while True:
        start_date_input = input("Enter the start date (YYYY-MM-DD): ").strip()
        try:
            start_date = datetime.strptime(start_date_input, "%Y-%m-%d")
            print(f"Using start date: {start_date.strftime('%Y-%m-%d')}")
            return start_date
        except ValueError:
            print("Invalid date format. Please enter in 'YYYY-MM-DD' format.")

# Load keywords
keywords = load_keywords()
if not keywords:
    print("No keywords provided. Exiting.")
    exit()

# Get start date
start_date = get_start_date()

# Extract domain name from the URL for CSV naming
url = "https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page"
domain = url.split("//")[-1].split("/")[0]  # Extract domain (e.g., "etenders.gov.in")
csv_filename = f"{domain}_{start_date.strftime('%Y-%m-%d')}.csv"

# Setup Selenium WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Initialize results list
tenders = []

def scrape_tenders():
    try:
        driver.get(url)
        time.sleep(15)  # Allow the page to load

        # Prompt user for Yes/No input
        user_input = input("Please solve the CAPTCHA manually. Type 'yes' to continue or 'no' to cancel: ").strip().lower()
        if user_input != "yes":
            print("Exiting the scraper as per user input.")
            return  # Exit the function

        while True:
            # Locate the table body
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="table"]/tbody'))
            )
            table_body = driver.find_element(By.XPATH, '//*[@id="table"]/tbody')

            # Find all rows in the table
            rows = table_body.find_elements(By.TAG_NAME, "tr")
            print(f"Found {len(rows)} rows on this page.")

            stop_scraping = False

            for row in rows[1:]:  # Skip the header row
                columns = row.find_elements(By.TAG_NAME, "td")
                if len(columns) >= 7:
                    # Extract tender details
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

                    # Convert and filter by date
                    try:
                        published_date = datetime.strptime(published_date_str, "%d-%b-%Y %I:%M %p")
                    except ValueError as e:
                        print(f"Date parsing error: {e}, skipping row.")
                        continue

                    # Stop scraping if published_date is older than start_date
                    if published_date < start_date:
                        print(f"Published date {published_date_str} is earlier than start date. Stopping.")
                        stop_scraping = True
                        break

                    # Keyword filtering across all key-value pairs
                    matched = any(kw.lower() in tender_title.lower() for kw in keywords)

                    if matched:
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

            if stop_scraping:
                break

            # Check for the 'Next' button
            try:
                next_button = driver.find_element(By.ID, "loadNext")
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                next_button.click()
                time.sleep(5)  # Allow the next page to load
            except Exception as e:
                print(f"No Next button found or clickable: {e}")
                break

    finally:
        driver.quit()

# Run scraper
scrape_tenders()

# Save results to CSV
if tenders:
    df = pd.DataFrame(tenders)
    df.to_csv(csv_filename, index=False)
    print(f"Scraping completed! Results saved to '{csv_filename}'.")
else:
    print("No matching tenders found.")
