from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
from datetime import datetime

# Set up Selenium WebDriver in Headless Mode
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Run in headless mode (No browser window)
options.add_argument("--disable-gpu")  # Disable GPU acceleration
options.add_argument("--no-sandbox")  # Bypass OS security model
options.add_argument("--disable-dev-shm-usage")  # Prevent resource exhaustion
options.add_argument("--window-size=1920x1080")  # Set window size to avoid element detection issues
driver = webdriver.Chrome(options=options)

# Open the GeM website
url = "https://bidplus.gem.gov.in/advance-search"
driver.get(url)
wait = WebDriverWait(driver, 10)

# Step 1: Ask the user to select the Organization
print("\n🔹 Choose the Organization:")
print("1️⃣ OIL AND NATURAL GAS CORPORATION LIMITED")
print("2️⃣ OIL INDIA LIMITED")

while True:
    choice = input("\nEnter your choice (1 or 2): ").strip()
    if choice == "1":
        selected_organization = "OIL AND NATURAL GAS CORPORATION LIMITED"
        break
    elif choice == "2":
        selected_organization = "OIL INDIA LIMITED"
        break
    else:
        print("❌ Invalid choice! Please enter 1 or 2.")

print(f"\n✅ Selected Organization: {selected_organization}")

# Step 2: Ask the user to enter Start Date and End Date
while True:
    start_date = input("\nEnter the Start Date (YYYY-MM-DD): ").strip()
    end_date = input("Enter the End Date (YYYY-MM-DD): ").strip()
    
    # Validate Date Format
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
        print(f"\n✅ Selected Date Range: {start_date} to {end_date}")
        break
    except ValueError:
        print("❌ Invalid date format! Please enter dates in YYYY-MM-DD format.")

# Step 3: Click "Search by Ministry / Organization"
ministry_tab = wait.until(EC.element_to_be_clickable((By.ID, "ministry-tab")))
ministry_tab.click()
time.sleep(2)

# Step 4: Select "MINISTRY OF PETROLEUM AND NATURAL GAS"
ministry_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@id='ministry']/following-sibling::span")))
ministry_dropdown.click()
time.sleep(1)

ministry_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'MINISTRY OF PETROLEUM AND NATURAL GAS')]")))
ministry_option.click()

# Step 5: Select the Organization (based on user choice)
organization_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@id='organization']/following-sibling::span")))
organization_dropdown.click()
time.sleep(1)

organization_option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//li[contains(text(), '{selected_organization}')]")))
organization_option.click()

# Step 6: Select "Bid End Date (From)" and "Bid End Date (To)"
driver.execute_script("document.getElementById('bidendFromMinistrySearch').removeAttribute('readonly')")
driver.execute_script("document.getElementById('bidendToMinistrySearch').removeAttribute('readonly')")
time.sleep(1)

from_date = wait.until(EC.element_to_be_clickable((By.ID, "bidendFromMinistrySearch")))
to_date = wait.until(EC.element_to_be_clickable((By.ID, "bidendToMinistrySearch")))

from_date.clear()
from_date.send_keys(start_date)
time.sleep(1)

to_date.clear()
to_date.send_keys(end_date)
time.sleep(1)

# Close the date picker
driver.find_element(By.TAG_NAME, "body").click()
time.sleep(1)

# Step 7: Locate and Debug Search Button
try:
    search_button = wait.until(EC.presence_of_element_located((By.ID, "searchByBid")))

    # Scroll to ensure visibility
    driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
    time.sleep(1)

    try:
        driver.execute_script("searchBid('ministry-search')")
        print("✅ Search Button triggered successfully!")
    except Exception as e:
        print("❌ Search Button trigger failed:", str(e))


except Exception as e:
    print("❌ Search button not found or could not be clicked:", str(e))


# **Extract Tender Details**
time.sleep(5)  # Allow full loading

try:
    wait.until(EC.presence_of_element_located((By.ID, "result")))
    print("✅ Results section loaded successfully!")
except:
    print("❌ Results section did not load.")
    driver.quit()
    exit()

# Define keywords (converted to lowercase for case-insensitive matching)
keywords = ["hoses", "pdc bits", "gate valves", "ball valves", "check valves", 
            "chokes", "well heads", "well test equipment", "christmas tree", "bop", "blowout preventer",
            "manifolds", "well contain", "onshore", "offshore", "subsea applications",
            "hi-lo safety valves", "charter hire rigs" "remote monitoring", "realtime monitoring", "well stimulation",
            "acidizing", "hf / hcl" "mopu","engineering  services", "lost circulation control additive", "lcca", "cement additive",
            "downhole gauges", "tubing encapsulated cable", "control line",
            "drone", "pipers", "free floating pipers", "downhole gauges", "control line"
            "carbon mapping", "carbon footprint", "ccus", "live rig monitoring", "analytics", "production testing services",
            "heavy weight drill pipe", "drill collars", "enhanced oil recovery", "esp"]

# **Initialize Tender List**
tender_list = []

# **Loop Through All Pages**
page_num = 1

while True:
    print(f"\n📄 Extracting data from Page {page_num}...")

    # **Wait for results to load**
    try:
        wait.until(EC.presence_of_element_located((By.ID, "result")))
        print("✅ Results section loaded successfully!")
    except:
        print("❌ Results section did not load.")
        break

    # **Find All Tenders**
    tenders = driver.find_elements(By.CSS_SELECTOR, "#bidCard .card")
    print(f"✅ Found {len(tenders)} tenders on Page {page_num}!")

    # **Loop Through All Tenders**
    for tender in tenders:
        try:
            bid_no = tender.find_element(By.CSS_SELECTOR, ".bid_no a").text
            bid_link = tender.find_element(By.CSS_SELECTOR, ".bid_no a").get_attribute("href")
        except:
            bid_no, bid_link = "N/A", "N/A"
        
        try:
            item_desc = tender.find_element(By.CSS_SELECTOR, ".col-md-4 a").get_attribute("data-content")  # Extract full description
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
            start_date = tender.find_element(By.CSS_SELECTOR, ".start_date").text
        except:
            start_date = "N/A"
        
        try:
            end_date = tender.find_element(By.CSS_SELECTOR, ".end_date").text
        except:
            end_date = "N/A"

        # **Convert item description to lowercase**
        item_desc_lower = item_desc.lower()

        # **Check if any keyword is in the item description**
        if any(keyword in item_desc_lower for keyword in keywords):
            tender_list.append({
                "BID NO": bid_no,
                "Link": bid_link,
                "Item Description": item_desc,
                "Quantity": quantity,
                "Department": department,
                "Start Date": start_date,
                "End Date": end_date,
                "Page": page_num
            })
            print(f"✅ Matched Tender: {bid_no} - {item_desc[:50]}...")

    # **Find and Click "Next" Button**
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "a.page-link.next")
        driver.execute_script("arguments[0].scrollIntoView();", next_button)  # Scroll to make sure button is visible
        time.sleep(1)
        next_button.click()
        page_num += 1
        time.sleep(3)  # Wait for the new page to load
    except:
        print("\n✅ No more pages left. Exiting...")
        break


# **Save Data to Excel**
today = datetime.today().strftime("%Y-%m-%d")
org_short = selected_organization.replace(" ", "_").lower()
filename = f"{today}-{org_short}.xlsx"

df = pd.DataFrame(tender_list)
df.to_excel(filename, index=False)
print(f"\n✅ Filtered tender data saved to '{filename}'")

driver.quit()
