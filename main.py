from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from PIL import Image
from time import sleep
import streamlit as st
import re


# ---------- Selenium functions ----------
def start_browser() -> webdriver.Chrome:
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    browser = webdriver.Chrome(options=chrome_options)
    browser.get('https://www.ebay.com/')
    return browser


def login_to_ebay(browser, username, password):
    try:
        browser.find_element(By.LINK_TEXT, "Sign in").click()
        sleep(2)
        browser.find_element(By.ID, "userid").send_keys(username)
        browser.find_element(By.ID, "signin-continue-btn").click()
        sleep(2)
        browser.find_element(By.ID, "pass").send_keys(password)
        browser.find_element(By.ID, "sgnBt").click()
        sleep(3)

        if browser.find_elements(By.ID, "send-button"):
            browser.find_element(By.ID, "send-button").click()
            sleep(8)
            return "verification_needed"

        if "sign in" in browser.current_url.lower():
            return False
        return True
    except Exception as e:
        print("Login error:", e)
        return False


def is_valid(browser, url, bid_price):
    try:
        browser.get(url)
        sleep(2)

        if "Item sold" in browser.page_source or "Bidding ended" in browser.page_source:
            return False, "The auction has ended."

        try:
            price_container = browser.find_element(By.CSS_SELECTOR, 'div.x-price-primary span.ux-textspans')
            current_price_text = price_container.text
        except NoSuchElementException:
            return False, "Could not locate the item price on the page."

        price_match = re.search(r"[\d,]+\.\d{2}", current_price_text)
        if not price_match:
            return False, f"Couldn't parse price from: {current_price_text}"

        current_price = float(price_match.group(0).replace(",", ""))
        if float(bid_price) <= current_price:
            return False, f"Your bidding price ({bid_price}) must be higher than the current price ({current_price:.2f})."

        return True, f"Valid bid. Current price: {current_price:.2f}"

    except Exception as e:
        return False, f"Error checking bid: {str(e)}"


def get_seconds_until_end(browser):
    try:
        time_text_element = browser.find_element(By.CSS_SELECTOR, 'span.ux-timer__text')
        full_text = time_text_element.text.replace("Ends in", "").strip()

        days = hours = minutes = seconds = 0
        day_match = re.search(r"(\d+)d", full_text)
        hour_match = re.search(r"(\d+)h", full_text)
        min_match = re.search(r"(\d+)m", full_text)
        sec_match = re.search(r"(\d+)s", full_text)

        if day_match: days = int(day_match.group(1))
        if hour_match: hours = int(hour_match.group(1))
        if min_match: minutes = int(min_match.group(1))
        if sec_match: seconds = int(sec_match.group(1))

        return days * 86400 + hours * 3600 + minutes * 60 + seconds, None
    except Exception as e:
        return None, f"Failed to get auction end time: {e}"


def place_bid(browser, bid_price):
    try:
        place_bid_button = browser.find_element(By.XPATH, '//span[text()="Place bid"]/ancestor::button')
        place_bid_button.click()
        sleep(2)

        input_box = browser.find_element(By.CSS_SELECTOR, 'input[type="tel"].textbox__control')
        input_box.clear()
        input_box.send_keys(str(bid_price))
        sleep(1)

        bid_button = browser.find_element(By.XPATH, '//button[normalize-space()="Bid"]')
        if bid_button.is_enabled():
            bid_button.click()
            # for self-control
            # st.write("Yayyyyyyyyyyy")
            return True, "Bid submitted successfully!"
        else:
            return False, "The 'Bid' button is not enabled because the bid value is too low."
    except Exception as e:
        return False, f"Failed to place bid: {e}"


def check_auction_result(browser):
    try:
        sleep(7)
        page_text = browser.page_source.lower()
        return "congratulations" in page_text
    except Exception:
        return False


# ---------- Streamlit UI ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    image = Image.open("C:/Users/user/PycharmProjects/MySniper/logo.png")
    st.image(image, width=300)

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'signed_in' not in st.session_state:
    st.session_state.signed_in = False

if st.session_state.step == 1:
    username = st.text_input("Enter your eBay Username or Email")
    password = st.text_input("Enter your Password", type="password")

    if st.button("Sign In"):
        st.session_state.browser = start_browser()
        result = login_to_ebay(st.session_state.browser, username, password)
        st.session_state.login_result = result

if 'login_result' in st.session_state and st.session_state.step == 1:
    if st.session_state.login_result == True:
        st.session_state.signed_in = True
        st.session_state.step = 2
    elif st.session_state.login_result == "verification_needed":
        st.info("A verification code has been sent to your email. Please enter the code below.")
        st.session_state.verification_wait = True
        st.session_state.step = "verification"
    elif st.session_state.login_result == False:
        st.error("The Username or Password provided are incorrect.")

if st.session_state.step == "verification":
    if 'verification_wait' in st.session_state and st.session_state.verification_wait:
        sleep(3)
        st.session_state.verification_wait = False

    st.info("Enter the verification code sent to your email:")
    verification_code = st.text_input("Verification Code")

    if st.button("Verify Code"):
        try:
            code_input = st.session_state.browser.find_element(By.ID, "code")
            code_input.send_keys(verification_code)
            st.session_state.browser.find_element(By.ID, "validate-code-button").click()
            sleep(3)
            skip_button = st.session_state.browser.find_element(By.ID, "passkeys-cancel-btn")
            skip_button.click()
            sleep(2)
            if "sign in" not in st.session_state.browser.current_url.lower():
                st.session_state.signed_in = True
                st.session_state.step = 2
            else:
                st.error("Verification code is incorrect or expired.")
        except Exception as e:
            st.error("Failed to verify the code.")

# Step 2: Submit bid
if st.session_state.step == 2 and st.session_state.signed_in:
    item_url = st.text_input("Enter the eBay Item URL")
    bid_price = st.text_input("Enter your Bidding Price")
    seconds_before_end = st.number_input("Enter number of seconds before auction end to place bid",
                                         min_value=5, max_value=3600)

    if st.button("Submit my offer"):
        valid, message = is_valid(st.session_state.browser, item_url, bid_price)
        if not valid:
            st.error(message)
        else:
            st.session_state.item_url = item_url
            st.session_state.bid_price = bid_price
            st.session_state.seconds_before_end = seconds_before_end
            st.info("✅ Offer submitted. Waiting for the right time to bid...")
            st.session_state.step = 3

# Step 3: Sniping
if st.session_state.step == 3:
    time_placeholder = st.empty()
    while True:
        # st.session_state.browser.get(st.session_state.item_url)
        st.session_state.browser.refresh()
        sleep(1.5)

        valid, message = is_valid(st.session_state.browser,
                                  st.session_state.item_url,
                                  st.session_state.bid_price)
        if not valid:
            st.markdown("### 😢 You didn’t win this time, but keep going – the next one’s yours!")
            break

        time_left, error = get_seconds_until_end(st.session_state.browser)
        if error:
            st.error(error)
            break

        # ✅ Dynamically update the visible time left
        time_placeholder.write(f"Auction ends in {time_left} seconds")

        # Note: it takes maximum ~9 seconds for the item's page to be refreshed
        if time_left <= int(st.session_state.seconds_before_end) + 9:
            st.info("Time reached! Submitting your bid now...")
            success, msg = place_bid(st.session_state.browser, st.session_state.bid_price)
            if success:
                st.success(msg)
            else:
                st.error(msg)
            sleep(1)
            st.session_state.step = 4
            break
        elif time_left > 60:
            sleep(5)
        else:
            sleep(1)

# Step 4: Check result
if st.session_state.step == 4:
    # Note: This check works best for last-second bidding.
    # If you bid early, eBay may not immediately update the
    # result, and you might see a "loss" message even if you eventually win.
    won = check_auction_result(st.session_state.browser)
    if won:
        st.markdown("### 🎉 Congratulations! You won the auction!")
    else:
        st.markdown("### 😢 You didn’t win this time, but keep going – the next one’s yours!")


# Debug info
# st.write("Current step:", st.session_state.step)
# st.write("Signed in:", st.session_state.signed_in)

# Optional manual override (for testing)
# if st.button("Force to Step 2"):
#     st.session_state.step = 2
#     st.session_state.signed_in = True

# Footer
st.markdown("---")
st.markdown("### Dedicated to Papa - you are always be the winner ❤️")
