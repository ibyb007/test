import os
import sys
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import re  # For URL filtering

# Debug print to confirm script start
print("Starting fetch_stream.py - Fetching ICC TV live streams...")

# Set up Chrome options for headless mode in CI with logging for network requests
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--disable-features=VizDisplayCompositor')
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
# Enable performance logging to capture network requests (for m3u8)
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

try:
    driver = webdriver.Chrome(options=chrome_options)
    print("Chrome driver initialized successfully.")
except Exception as e:
    print(f"Error initializing Chrome driver: {e}")
    sys.exit(1)

# ICC TV URLs
login_url = "https://www.icc-cricket.com/signin"
stream_url = "https://www.icc-cricket.com/icc-tv"  # Main ICC TV page; may redirect to live if event ongoing

# Get credentials from env
username = os.environ.get('ICC_USERNAME')
password = os.environ.get('ICC_PASSWORD')
if not username or not password:
    print("Error: ICC_USERNAME or ICC_PASSWORD not set in environment.")
    sys.exit(1)

try:
    # Step 1: Login
    print("Navigating to login page...")
    driver.get(login_url)
    wait = WebDriverWait(driver, 10)

    # Fill login form (adjust selectors if needed based on inspection)
    email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))  # Common ID for email
    email_input.clear()
    email_input.send_keys(username)

    pwd_input = driver.find_element(By.ID, "password")  # Common ID for password
    pwd_input.clear()
    pwd_input.send_keys(password)

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-primary")  # Submit button
    submit_btn.click()

    # Wait for login success (e.g., redirect or dashboard element)
    time.sleep(3)  # Brief wait for auth
    if "signin" in driver.current_url.lower():
        raise Exception("Login failed - still on signin page.")
    print("Login successful.")

    # Step 2: Navigate to live streams page
    print(f"Navigating to ICC TV: {stream_url}")
    driver.get(stream_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))  # Wait for page load
    print("ICC TV page loaded.")

    # Optional: If there's a 'Live Now' button or match selector, click it
    try:
        live_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='live-match'], .live-stream-btn")))  # Example selector
        live_btn.click()
        time.sleep(2)
        print("Clicked on live match.")
    except TimeoutException:
        print("No live match button found - checking for ongoing events.")

    # Step 3: Extract m3u8 streams from network logs
    # Get performance logs
    logs = driver.get_log('performance')
    streams = []
    for entry in logs:
        message = json.loads(entry['message'])['message']
        if message['method'] == 'Network.responseReceived':
            url = message['params']['response']['url']
            if re.search(r'\.m3u8(\?.*)?$', url):  # Match .m3u8 URLs (HLS streams)
                # Filter for ICC-related or video streams
                if 'icc' in url.lower() or 'hls' in url.lower() or 'live' in url.lower():
                    streams.append(url)
                    print(f"Found potential stream: {url}")

    if not streams:
        print("No m3u8 streams found in network logs. No live ICC TV streams available?")
        # Fallback: Try to find video src directly
        try:
            video_elem = driver.find_element(By.TAG_NAME, "video")
            stream_src = video_elem.get_attribute("src")
            if stream_src and '.m3u8' in stream_src:
                streams.append(stream_src)
                print(f"Found video src stream: {stream_src}")
        except NoSuchElementException:
            pass

except WebDriverException as e:
    print(f"WebDriverException during ICC TV access: {e}")
    print("This could be due to geo-restrictions, no live events, or auth issues.")
    streams = []
except Exception as e:
    print(f"Unexpected error: {e}")
    streams = []
finally:
    driver.quit()

print(f"Extracted {len(streams)} valid streams.")

# Generate M3U content
m3u_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
if not streams:
    m3u_content += "# No live ICC TV streams available at this time.\n"
else:
    for i, url in enumerate(streams, 1):
        title = f"ICC TV Live Stream {i}"
        m3u_content += f"#EXTINF:-1 tvg-logo=\"ICC\" group-title=\"ICC TV Live\",{title}\n"
        m3u_content += f"{url}\n"

# Ensure exact filename with space for workflow compatibility
filename = "icc live.m3u"
with open(filename, 'w', encoding='utf-8') as f:
    f.write(m3u_content)

# Verify file creation
if os.path.exists(filename) and os.path.getsize(filename) > 0:
    print(f"M3U file '{filename}' created successfully with {len(streams)} streams.")
    with open(filename, 'r') as f:
        content = f.read()
        print("M3U preview (first 200 chars):")
        print(content[:200] + "..." if len(content) > 200 else content)
else:
    print(f"Error: M3U file '{filename}' not created or empty.")
    sys.exit(1)

print("Script completed successfully.")
