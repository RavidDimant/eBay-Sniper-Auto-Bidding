from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
from time import sleep
import streamlit as st
import re
import pandas as pd


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
        # Step 1: Click the "Place bid" button
        place_bid_button = browser.find_element(By.XPATH, '//span[text()="Place bid"]/ancestor::button')
        place_bid_button.click()

        # Step 2: Enter bid value
        input_box = WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="tel"].textbox__control'))
        )
        input_box.clear()
        input_box.send_keys(str(bid_price))
        sleep(1.5)

        # Step 3: Clicking on "Bid" button
        bid_buttons = browser.find_elements(By.CSS_SELECTOR,
                                            'div.place-bid-actions__submit > button.btn--fluid.btn--primary')
        bid_button = next((btn for btn in bid_buttons if btn.text.strip() == "Bid"), None)
        if bid_button and bid_button.is_enabled():
            bid_button.click()
            # for self-control
            # st.write("Yayyyyyyyyyyy")
            return True, "Bid submitted successfully!"
        else:
            return False, "Bid button not available or not enabled."
    except Exception as e:
        return False, f"Failed to place bid: {e}"


def check_auction_result(browser):
    try:
        sleep(6)
        page_text = browser.page_source.lower()
        return "congratulations" in page_text
    except Exception:
        return False


# ---------- Streamlit UI ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    image = Image.open("logo.png")
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


# Step 2: Submit bid (Modified for multiple items)
if st.session_state.step == 2 and st.session_state.signed_in:
    # Initialize items dictionary if not exists
    if 'items_dict' not in st.session_state:
        st.session_state.items_dict = {}
    if 'current_item_index' not in st.session_state:
        st.session_state.current_item_index = 0
    if 'results_summary' not in st.session_state:
        st.session_state.results_summary = []
    
    # Initialize input values in session state
    if 'item_url_input' not in st.session_state:
        st.session_state.item_url_input = ""
    if 'bid_price_input' not in st.session_state:
        st.session_state.bid_price_input = ""
    
    st.markdown("### Add Items to Bid On")
    
    # Display current items
    if st.session_state.items_dict:
        st.markdown("**Current Items:**")
        for i, (url, price) in enumerate(st.session_state.items_dict.items()):
            st.write(f"{i+1}. URL: {url[:50]}... | Bid Price: ${price}")
    
    # Input fields for new item
    with st.form("add_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            item_url = st.text_input("Enter the eBay Item URL", value=st.session_state.item_url_input)
        with col2:
            bid_price = st.text_input("Enter your Bidding Price", value=st.session_state.bid_price_input)
        submitted = st.form_submit_button("Add Item to List")
    
    # Add item button
    if submitted:
        if item_url and bid_price:
            try:
                # Validate the item before adding
                valid, message = is_valid(st.session_state.browser, item_url, bid_price)
                if valid:
                    st.session_state.items_dict[item_url] = float(bid_price)
                    st.success(f"✅ Item added successfully! {message}")
                    st.rerun()
                else:
                    st.error(f"❌ Cannot add item: {message}")
            except Exception as e:
                st.error(f"❌ Error validating item: {str(e)}")
        else:
            st.error("Please enter both URL and bid price")

    
    # Remove last item button
    if st.session_state.items_dict and st.button("Remove Last Item"):
        last_url = list(st.session_state.items_dict.keys())[-1]
        del st.session_state.items_dict[last_url]
        st.success("Last item removed")
        st.rerun()
    
    # Clear all items button
    if st.session_state.items_dict and st.button("Clear All Items"):
        st.session_state.items_dict = {}
        st.session_state.current_item_index = 0
        st.session_state.results_summary = []
        st.session_state.item_url_input = ""
        st.session_state.bid_price_input = ""
        st.success("All items cleared")
        st.rerun()
    
    # Start bidding button
    if st.session_state.items_dict:
        seconds_before_end = st.number_input("Enter number of seconds before auction end to place bid",
                                             min_value=5, max_value=3600)
        
        if st.button("Start Bidding on All Items"):
            st.session_state.seconds_before_end = seconds_before_end
            st.session_state.current_item_index = 0
            st.session_state.results_summary = []
            st.info("✅ Starting bidding process...")
            st.session_state.step = 3


# Step 3: Sniping (Modified for multiple items)
if st.session_state.step == 3:
    # Get current item from dictionary
    items_list = list(st.session_state.items_dict.items())
    
    if st.session_state.current_item_index < len(items_list):
        current_url, current_bid_price = items_list[st.session_state.current_item_index]
        
        st.markdown(f"### Bidding on Item {st.session_state.current_item_index + 1} of {len(items_list)}")
        # st.write(f"**URL:** {current_url}")
        # st.write(f"**Bid Price:** ${current_bid_price}")
        
        time_placeholder = st.empty()
        status_placeholder = st.empty()
        
        while True:
            st.session_state.browser.get(current_url)
            sleep(1.5)

            valid, message = is_valid(st.session_state.browser, current_url, current_bid_price)
            if not valid:
                status_placeholder.markdown("### 😢 You didn't win this time, but keep going – the next one's yours!")
                # Record result
                st.session_state.results_summary.append({
                    'url': current_url,
                    'bid_price': current_bid_price,
                    'result': 'X'
                })
                break

            time_left, error = get_seconds_until_end(st.session_state.browser)
            if error:
                status_placeholder.error(error)
                # Record result
                st.session_state.results_summary.append({
                    'url': current_url,
                    'bid_price': current_bid_price,
                    'result': 'X'
                })
                break

            # Dynamically update the visible time left
            time_placeholder.write(f"Auction ends in {time_left} seconds")

            # Note: it takes maximum ~10 seconds for the item's page to be refreshed
            if time_left <= int(st.session_state.seconds_before_end) + 10:
                status_placeholder.info("Time reached! Submitting your bid now...")
                success, msg = place_bid(st.session_state.browser, current_bid_price)
                if success:
                    status_placeholder.success(msg)
                    # Check if we actually won the auction
                    won_auction = check_auction_result(st.session_state.browser)
                    # Record result based on actual auction outcome
                    st.session_state.results_summary.append({
                        'url': current_url,
                        'bid_price': current_bid_price,
                        'result': 'V' if won_auction else 'X'
                    })
                else:
                    status_placeholder.error(msg)
                    # Record result
                    st.session_state.results_summary.append({
                        'url': current_url,
                        'bid_price': current_bid_price,
                        'result': 'X'
                    })
                sleep(1)
                break
            elif time_left > 60:
                sleep(5)
            else:
                sleep(1)
        
        # Move to next item
        st.session_state.current_item_index += 1
        
        if st.session_state.current_item_index >= len(items_list):
            st.session_state.step = 4
        else:
            sleep(2)  # Brief pause before next item
            st.rerun()
    else:
        st.session_state.step = 4

# Step 4: Results Summary
if st.session_state.step == 4:
    st.markdown("### 🎯 Bidding Results Summary")
    
    if st.session_state.results_summary:
        # Create results table
        results_data = []
        for i, result in enumerate(st.session_state.results_summary):
            # Create clickable URL that opens in new tab
            url_display = result['url'][:50] + '...' if len(result['url']) > 50 else result['url']
            clickable_url = f'<a href="{result["url"]}" target="_blank">{url_display}</a>'
            
            results_data.append({
                'Item #': i + 1,
                'URL': clickable_url,
                'Bid Price': f"${result['bid_price']}",
                'Result': '✅ Won' if result['result'] == 'V' else '❌ Lost'
            })
        
        df = pd.DataFrame(results_data)
        # Use st.markdown with unsafe_allow_html=True to render HTML links
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # Summary statistics
        total_items = len(st.session_state.results_summary)
        won_items = sum(1 for r in st.session_state.results_summary if r['result'] == 'V')
        lost_items = total_items - won_items
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Items", total_items)
        with col2:
            st.metric("Won", won_items, delta=f"{won_items/total_items*100:.1f}%" if total_items > 0 else "0%")
        with col3:
            st.metric("Lost", lost_items, delta=f"{lost_items/total_items*100:.1f}%" if total_items > 0 else "0%")
        
        # Overall message
        if won_items > 0:
            st.markdown("### 🎉 Congratulations! You won some auctions!")
        else:
            st.markdown("### 😢 Better luck next time! Keep trying!")
        
        # Reset button
        if st.button("Start New Bidding Session"):
            st.session_state.step = 2
            st.session_state.items_dict = {}
            st.session_state.current_item_index = 0
            st.session_state.results_summary = []
            st.rerun()
    else:
        st.info("No results to display")


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