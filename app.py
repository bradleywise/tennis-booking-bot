import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import time

# --- CONFIGURATION ---
COURT_OPTIONS = [
    "McFetridge Tennis Ct01",
    "McFetridge Tennis Ct02",
    "McFetridge Tennis Ct03",
    "McFetridge Tennis Ct04",
    "McFetridge Tennis Ct05",
    "McFetridge Tennis Ct06"
]

# Generate hourly time slots (7 AM to 10 PM)
TIME_OPTIONS = [f"{hour % 12 or 12}:00 {'AM' if hour < 12 else 'PM'}" for hour in range(7, 23)]

def run_booking_bot(username, password, event_name, target_date, time_str, duration, court_name):
    status_text = st.empty()
    status_text.info("🚀 Bot starting...")

    # Setup Headless Chrome
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)

    try:
        # --- STEP 1: LOGIN ---
        status_text.info("🔑 Logging in...")
        driver.get("https://anc.apm.activecommunities.com/chicagoparkdistrict/signin")
        
        # Email
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter your Email address"]')))
        email_input.clear()
        email_input.send_keys(username)
        
        # Password
        pass_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        pass_input.clear()
        pass_input.send_keys(password)
        
        # Sign In Button
        driver.find_element(By.XPATH, "//button[contains(., 'Sign In')]").click()
        time.sleep(4) 

        # --- STEP 2: NAVIGATE TO RESERVATION ---
        status_text.info("📅 Navigating to reservation page...")
        driver.get("https://anc.apm.activecommunities.com/chicagoparkdistrict/reservation/landing/quick?groupId=2")
        time.sleep(3)

        # --- STEP 3: FILL SEARCH CRITERIA ---
        status_text.info("🔍 Entering booking details...")
        
        # Event Name
        try:
            event_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Event name"]')
            event_input.clear()
            event_input.send_keys(event_name)
        except Exception as e:
            st.warning(f"Event Name skipped: {e}")

        # Date Selection (JS Hack)
        formatted_date = target_date.strftime("%m/%d/%Y")
        try:
            date_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Date picker, current date"]')
            driver.execute_script(f"arguments[0].value = '{formatted_date}';", date_input)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", date_input)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", date_input)
            date_input.send_keys("\ue007") # Press Enter
        except Exception as e:
            st.error(f"Date selection failed: {e}")

        # Search
        try:
            driver.find_element(By.XPATH, "//button[contains(., 'Search') or @id='searchButton']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, ".btn-super").click()
            
        time.sleep(3)

        # --- STEP 4: FIND AND SELECT SLOTS ---
        status_text.info(f"⚡ Looking for {court_name} at {time_str}...")

        start_time_dt = datetime.strptime(time_str, "%I:%00 %p")
        slots_to_book = [start_time_dt]
        if duration == "2 Hours":
            slots_to_book.append(start_time_dt + timedelta(hours=1))

        selection_made = False
        
        for slot_time in slots_to_book:
            slot_str = slot_time.strftime("%I:%00 %p").lstrip("0") # "7:00 AM"
            
            try:
                # Find the cell for the specific court and time
                xpath = f"//td[contains(@aria-label, '{court_name}') and contains(@aria-label, '{slot_str}')]"
                booking_cell = driver.find_element(By.XPATH, xpath)
                booking_cell.click()
                time.sleep(1) # Short wait between clicks
                selection_made = True
                st.write(f"✅ Selected slot: {slot_str}")
            except:
                st.warning(f"Could not select {slot_str} (Might be unavailable)")

        if not selection_made:
            status_text.error("❌ No slots available to book.")
            return

        # --- STEP 5: CONFIRMATION SEQUENCE ---
        # "After the time the times are selected..."
        
        status_text.info("🔄 Processing Confirmations...")
        time.sleep(2) 

        # 1. Confirm Bookings
        try:
            st.write("Clicking 'Confirm Bookings'...")
            # Looks for button with exact text or close to it
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirm Bookings')]")))
            btn.click()
            time.sleep(3) # Wait for page transition
        except Exception as e:
            st.error(f"Failed at 'Confirm Bookings': {e}")
            return

        # 2. Reserve
        try:
            st.write("Clicking 'Reserve'...")
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Reserve')]")))
            btn.click()
            time.sleep(3)
        except Exception as e:
            st.error(f"Failed at 'Reserve': {e}")
            return

        # 3. Check out
        try:
            st.write("Clicking 'Check out'...")
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Check out') or contains(., 'Checkout')]")))
            btn.click()
            time.sleep(3)
        except Exception as e:
            st.error(f"Failed at 'Check out': {e}")
            return

        # 4. Pay (Final Step)
        try:
            st.write("Clicking 'Pay'...")
            # Note: This often requires saved credit card on file
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Pay')]")))
            btn.click()
            status_text.success("🎉 Payment clicked! Reservation should be complete.")
            time.sleep(5) # Let payment process
        except Exception as e:
            st.error(f"Failed at 'Pay' button: {e}")

    except Exception as e:
        st.error(f"Critical Bot Error: {e}")
    finally:
        driver.quit()

# --- STREAMLIT FRONT END ---
st.set_page_config(page_title="serveBot", page_icon="🎾")
st.title("serveBot 3.0")

with st.form("booking_form"):
    c1, c2 = st.columns(2)
    with c1:
        user = st.text_input("Username (Email)")
        event_name = st.text_input("Event Name", value="Tennis Practice")
    with c2:
        pw = st.text_input("Password", type="password")
        court = st.selectbox("Select Court", COURT_OPTIONS)

    c3, c4, c5 = st.columns(3)
    with c3:
        default_date = datetime.now() + timedelta(days=7)
        d = st.date_input("Date", value=default_date)
    with c4:
        t = st.selectbox("Start Time", TIME_OPTIONS, index=TIME_OPTIONS.index("07:00 AM") if "07:00 AM" in TIME_OPTIONS else 0)
    with c5:
        dur = st.selectbox("Duration", ["1 Hour", "2 Hours"])

    st.warning("⚠️ Ensure you have a Credit Card saved on your account, or the 'Pay' step may fail.")
    submitted = st.form_submit_button("Hit Ace")

if submitted:
    if not user or not pw:
        st.error("Please enter credentials.")
    else:
        run_booking_bot(user, pw, event_name, d, t, dur, court)
