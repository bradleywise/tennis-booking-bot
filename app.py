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
    """
    Main logic to run the browser and book the court.
    """
    status_text = st.empty()
    status_text.info("🚀 Bot starting...")

    # Setup Headless Chrome
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080') # Ensure grid is visible
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # --- STEP 1: LOGIN ---
        status_text.info("🔑 Logging in...")
        driver.get("https://anc.apm.activecommunities.com/chicagoparkdistrict/signin")
        
        # New Login Logic based on your inspected HTML
        # Email Input
        email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter your Email address"]')))
        email_input.clear()
        email_input.send_keys(username)
        
        # Password Input (standard type="password")
        pass_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')
        pass_input.clear()
        pass_input.send_keys(password)
        
        # Click Sign In (Using text matching to be safe)
        driver.find_element(By.XPATH, "//button[contains(., 'Sign In')]").click()
        
        # Wait for login to finish (check if URL changes or 'Sign Out' appears)
        time.sleep(5) 

        # --- STEP 2: NAVIGATE TO RESERVATION ---
        status_text.info("📅 Navigating to reservation page...")
        # Direct link to Quick Reserve group
        driver.get("https://anc.apm.activecommunities.com/chicagoparkdistrict/reservation/landing/quick?groupId=2")
        time.sleep(3)

        # --- STEP 3: FILL SEARCH CRITERIA ---
        status_text.info("🔍 Entering booking details...")
        
        # 3A. EVENT NAME
        # Based on your HTML: aria-label="Event name"
        try:
            event_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Event name"]')
            event_input.clear() # Clear the "test" value
            event_input.send_keys(event_name)
        except Exception as e:
            st.warning(f"Could not find Event Name box: {e}")

        # 3B. DATE SELECTION
        # Complex widget with inputmode="none". We use JavaScript to force the value.
        formatted_date = target_date.strftime("%m/%d/%Y") # Standard US format
        try:
            # Locate by aria-label provided
            date_input = driver.find_element(By.CSS_SELECTOR, 'input[aria-label="Date picker, current date"]')
            
            # JavaScript Hack: Set value directly and trigger 'change' event
            driver.execute_script(f"arguments[0].value = '{formatted_date}';", date_input)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", date_input)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", date_input)
            time.sleep(1)
            # Backup: Press Enter just in case
            date_input.send_keys("\ue007") # \ue007 is the Enter key
        except Exception as e:
            st.error(f"Date selection failed: {e}")

        # Click Search Button (Look for button with 'Search' text or icon)
        try:
            search_btn = driver.find_element(By.XPATH, "//button[contains(., 'Search') or @id='searchButton']")
            search_btn.click()
        except:
            # Sometimes specific ID needed
            driver.find_element(By.CSS_SELECTOR, ".btn-super").click()
            
        time.sleep(3) # Wait for grid to load

        # --- STEP 4: FIND AND BOOK SLOTS ---
        status_text.info(f"⚡ Looking for {court_name} at {time_str}...")

        # Calculate slots to book (1 or 2)
        # Convert user friendly "07:00 AM" -> datetime object
        start_time_dt = datetime.strptime(time_str, "%I:%00 %p")
        slots_to_book = [start_time_dt]
        
        if duration == "2 Hours":
            # Add the next hour
            slots_to_book.append(start_time_dt + timedelta(hours=1))

        # Loop through slots (Book 7:00, then Book 8:00)
        success_count = 0
        
        for slot_time in slots_to_book:
            slot_str = slot_time.strftime("%I:%00 %p").lstrip("0") # "7:00 AM" or "07:00 AM" depending on site
            
            try:
                # Construct XPath to find the specific white cell
                # Logic: Find Row with Court Name -> Find Cell in that row with specific Data Time (or column index)
                # Note: Exact HTML structure varies, but this is the most robust guess:
                
                # Option A: Look for aria-label or title usually on the cell
                # "McFetridge Tennis Ct01 7:00 AM Available"
                xpath = f"//td[contains(@aria-label, '{court_name}') and contains(@aria-label, '{slot_str}')]"
                
                # Option B (From your previous code): Data attribute
                # xpath = f"//td[contains(@data-time, '{slot_str}')]..." -> hard without knowing exact row
                
                # Let's try clicking the cell that has the time text if it's visible, or use the Aria Label approach which is standard for ActiveNet
                booking_cell = driver.find_element(By.XPATH, xpath)
                
                booking_cell.click()
                time.sleep(2)
                
                # Handle "Add to Cart" confirmation modal if it pops up
                try:
                    confirm_btn = driver.find_element(By.XPATH, "//button[contains(., 'Add to Cart') or contains(., 'Continue')]")
                    confirm_btn.click()
                    time.sleep(2)
                except:
                    pass # Maybe it just adds to cart immediately
                
                success_count += 1
                st.write(f"✅ Clicked slot: {slot_str}")
                
            except Exception as e:
                st.warning(f"Could not book {slot_str}: Slot might be taken or selector invalid.")
        
        if success_count > 0:
            status_text.success(f"🎉 Process Complete! {success_count} slot(s) selected. Please check your account to pay.")
        else:
            status_text.error("❌ Could not find any available slots matching your criteria.")

    except Exception as e:
        st.error(f"Critical Bot Error: {e}")
    finally:
        driver.quit()

# --- STREAMLIT FRONT END ---
st.set_page_config(page_title="Tennis Bot", page_icon="🎾")
st.title("🎾 Tennis Court Auto-Booker")
st.markdown("### Automated Reservation Tool")

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
        # Date picker: Default to 7 days from now
        default_date = datetime.now() + timedelta(days=7)
        d = st.date_input("Date", value=default_date)
    with c4:
        # Hourly selections only
        t = st.selectbox("Start Time", TIME_OPTIONS, index=TIME_OPTIONS.index("07:00 AM") if "07:00 AM" in TIME_OPTIONS else 0)
    with c5:
        dur = st.selectbox("Duration", ["1 Hour", "2 Hours"])

    st.warning("⚠️ Run this 2 minutes before 7:00 AM. The bot will log in and wait.")
    submitted = st.form_submit_button("🤖 Run Bot Now")

if submitted:
    if not user or not pw:
        st.error("Please enter your username and password.")
    else:
        run_booking_bot(user, pw, event_name, d, t, dur, court)
