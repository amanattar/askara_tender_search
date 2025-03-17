from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Set up Selenium WebDriver
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)

# Open the GeM website
url = "https://bidplus.gem.gov.in/advance-search"
driver.get(url)
wait = WebDriverWait(driver, 10)

# Step 2: Click "Search by Ministry / Organization"
ministry_tab = wait.until(EC.element_to_be_clickable((By.ID, "ministry-tab")))
ministry_tab.click()
time.sleep(2)

# Step 3: Select "MINISTRY OF PETROLEUM AND NATURAL GAS"
ministry_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@id='ministry']/following-sibling::span")))
ministry_dropdown.click()
time.sleep(1)

ministry_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'MINISTRY OF PETROLEUM AND NATURAL GAS')]")))
ministry_option.click()

# Step 4: Select "OIL AND NATURAL GAS CORPORATION LIMITED"
organization_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@id='organization']/following-sibling::span")))
organization_dropdown.click()
time.sleep(1)

organization_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'OIL AND NATURAL GAS CORPORATION LIMITED')]")))
organization_option.click()

# Step 5: Select "Bid End Date (From)" and "Bid End Date (To)"
driver.execute_script("document.getElementById('bidendFromMinistrySearch').removeAttribute('readonly')")
driver.execute_script("document.getElementById('bidendToMinistrySearch').removeAttribute('readonly')")
time.sleep(1)

from_date = wait.until(EC.element_to_be_clickable((By.ID, "bidendFromMinistrySearch")))
to_date = wait.until(EC.element_to_be_clickable((By.ID, "bidendToMinistrySearch")))

from_date.clear()
from_date.send_keys("2025-03-14")
time.sleep(1)

to_date.clear()
to_date.send_keys("2025-04-16")
time.sleep(1)

# Close the date picker
driver.find_element(By.TAG_NAME, "body").click()
time.sleep(1)

# Step 6: Locate and Debug Search Button
try:
    search_button = wait.until(EC.presence_of_element_located((By.ID, "searchByBid")))
    print("✅ Search button found!")
    print("Button Text:", search_button.text)
    print("Button HTML:", search_button.get_attribute("outerHTML"))

    # Scroll to ensure visibility
    driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
    time.sleep(1)

    try:
        print("Trying JavaScript function trigger...")
        driver.execute_script("searchBid('ministry-search')")
        print("✅ JavaScript function triggered successfully!")
    except Exception as e:
        print("❌ JavaScript function trigger failed:", str(e))


except Exception as e:
    print("❌ Search button not found or could not be clicked:", str(e))

# Keep browser open for review
input("Press Enter to close the browser...")

# Close browser
driver.quit()
