import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import time

# Streamlit front-end: User-friendly form
st.title("Tennis Court Booking Bot")
st.write("Enter your details and click 'Book Now' to automate the reservation. Run this at 7 AM for best results.")

# User inputs
username = st.text_input("Username/Email", type="default")
password = st.text_input("Password", type="password")
preferred_date = st.date_input("Preferred Date (must be exactly 7 days from now for new openings)")
preferred_time = st.time_input("Preferred Time (e.g., 10:00 AM)")
backup_time = st.time_input("Backup Time (if preferred is unavailable)")
court_name = st.text_input("Court Name (e.g., 'Court 1')", value="Court 1")  # Adjust based on site

if st.button("Book Now"):
    if not username or not password:
        st.error("Please enter username and password.")
    else:
        st.write("Starting bot... This may take a minute.")

        # Set up headless Chrome (runs in background)
        options = Options()
        options.add_argument('--headless')  # No visible browser window
        options.add_argument('--no-sandbox')  # Required for server environments
        options.add_argument('--disable-dev-shm-usage')  # Required for server
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        try:
            # Step 1: Go to login page and log in
            driver.get("https://anc.apm.activecommunities.com/chicagoparkdistrict/signin?onlineSiteId=0&from_original_cui=true&override_partial_error=False&custom_amount=False&params=aHR0cHM6Ly9hbmMuYXBtLmFjdGl2ZWNvbW11bml0aWVzLmNvbS9jaGljYWdvcGFya2Rpc3RyaWN0L3Jlc2VydmF0aW9uL2xhbmRpbmcvcXVpY2s%2FZ3JvdXBJZD0yJmZyb21Mb2dpblBhZ2U9dHJ1ZSZmcm9tX29yaWdpbmFsX2N1aT10cnVlJmZyb21Mb2dpblBhZ2U9dHJ1ZQ%3D%3D")
            time.sleep(2)  # Wait for page load

            # Enter username and password (adjust selectors if needed - see inspection guide below)
            driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Email address Required"]').send_keys(username)
            driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Password Required"]').send_keys(password)
            driver.find_element(By.CSS_SELECTOR, 'button.btn.btn-super').click()
            time.sleep(5)  # Wait for login to complete

            # Step 2: Go to reservation page
            driver.get("https://anc.apm.activecommunities.com/chicagoparkdistrict/reservation/landing/quick?groupId=2&fromLoginPage=true&from_original_cui=true")
            time.sleep(3)

            # Step 3: Select date (format as MM/DD/YYYY - adjust selector)
            date_str = preferred_date.strftime("%m/%d/%Y")
            driver.find_element(By.ID, "startDate").send_keys(date_str)  # Assume ID for date input; adjust if needed
            driver.find_element(By.ID, "searchButton").click()  # Assume ID for search button; adjust
            time.sleep(3)

            # Step 4: Try to book preferred time slot
            booked = False
            try:
                # Find the time slot cell (assume table with class 'reservation-table'; adjust XPath)
                preferred_time_str = preferred_time.strftime("%I:%M %p")
                slot_xpath = f"//td[contains(text(), '{court_name}')]/following-sibling::td[contains(@data-time, '{preferred_time_str}') and contains(@style, 'white')]"  # Looks for available (white) slot
                slot = driver.find_element(By.XPATH, slot_xpath)
                slot.click()
                time.sleep(2)
                # Confirm booking (adjust selector)
                driver.find_element(By.ID, "confirmButton").click()
                booked = True
                st.success("Booked preferred slot!")
            except:
                st.warning("Preferred slot unavailable. Trying backup...")

            # Step 5: If preferred fails, try backup
            if not booked:
                backup_time_str = backup_time.strftime("%I:%M %p")
                slot_xpath = f"//td[contains(text(), '{court_name}')]/following-sibling::td[contains(@data-time, '{backup_time_str}') and contains(@style, 'white')]"
                try:
                    slot = driver.find_element(By.XPATH, slot_xpath)
                    slot.click()
                    time.sleep(2)
                    driver.find_element(By.ID, "confirmButton").click()
                    st.success("Booked backup slot!")
                except:
                    st.error("Both slots unavailable. Try again later.")

        except Exception as e:
            st.error(f"Error: {str(e)}. Check selectors or site changes.")
        finally:
            driver.quit()  # Close browser
