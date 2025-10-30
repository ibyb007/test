import os
import sys
import json
import random  # For proxy selection
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import re  # For URL filtering

# Debug print to confirm script start
print("Starting fetch_stream.py - Fetching ICC TV live streams with geo-bypass...")

# Updated list of free proxies from allowed countries (prioritized: Germany, France, Netherlands, etc.)
PROXIES = [
    {"ip": "188.40.57.101", "port": "80", "country": "Germany", "type": "elite"},
    {"ip": "147.75.34.105", "port": "443", "country": "Netherlands", "type": "elite"},
    {"ip": "51.159.28.39", "port": "80", "country": "France", "type": "elite"},
    {"ip": "37.187.92.9", "port": "1026", "country": "France", "type": "elite"},
    {"ip": "109.135.16.145", "port": "8789", "country": "Belgium", "type": "elite"},
    {"ip": "45.144.234.129", "port": "53681", "country": "Finland", "type": "elite"},
    {"ip": "65.108.159.129", "port": "8081", "country": "Finland", "type": "elite"},
    {"ip": "138.124.49.149", "port": "10808", "country": "Sweden", "type": "elite"},
    {"ip": "8.220.141.8", "port": "1234", "country": "Philippines", "type": "elite"},
    {"ip": "14.251.13.0", "port": "8080", "country": "Vietnam", "type": "elite"},
    {"ip": "38.54.71.67", "port": "80", "country": "Nepal", "type": "elite"},
    {"ip": "46.47.197.210", "port": "3128", "country": "Russian Federation", "type": "elite"},
    {"ip": "159.224.213.97", "port": "8470", "country": "Ukraine", "type": "elite"},
    {"ip": "78.28.152.113", "port": "80", "country": "Bosnia and Herzegovina", "type": "elite"},
    {"ip": "8.210.17.35", "port": "9443", "country": "Hong Kong", "type": "elite"},
]

# Select a random proxy to avoid bans (or cycle through on failure)
proxy = random.choice(PROXIES)
proxy_server = f"http://{proxy['ip']}:{proxy['port']}"
print(f"Using proxy: {proxy_server} ({proxy['country']}, {proxy['type']})")

# Set up Chrome options for headless mode in CI with proxy and logging
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--disable-features=VizDisplayCompositor')
chrome_options.add_argument(f'--proxy-server={proxy_server}')  # Geo-bypass proxy
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
# Enable performance logging to capture network requests (for m3u8)
chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = None
try:
    driver = webdriver.Chrome(options=chrome_options)
    print("Chrome driver initialized successfully with proxy.")
except Exception as e:
    print(f"Error initializing Chrome driver with proxy {proxy_server}: {e}")
    # Fallback: Try without proxy or another one
    print("Falling back to no proxy...")
    chrome_options = Options()  # Reset options without proxy
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=VizDisplayCompositor')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Chrome driver initialized without proxy.")
    except Exception as e2:
        print(f"Fallback failed: {e2}")
        sys.exit(1)

# ICC TV URLs
login_url = "https://www.icc-cricket.com/signin"
stream_url = "https://www.icc-cricket.com/live"  # Updated to live streams page for Women's World Cup 2025 Semi-Final

# Get credentials from env
username = os.environ.get('ICC_USERNAME')
password = os.environ.get('ICC_PASSWORD')
if not username or not password:
    print("Error: ICC_USERNAME or ICC_PASSWORD not set in environment.")
    sys.exit(1)

streams = []
try:
    # Step 1: Login
    print("Navigating to login page...")
    driver.get(login_url)
    wait = WebDriverWait(driver, 15)  # Increased timeout for proxy

    # Fill login form (adjust selectors if needed)
    email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
    email_input.clear()
    email_input.send_keys(username)

    pwd_input = driver.find_element(By.ID, "password")
    pwd_input.clear()
    pwd_input.send_keys(password)

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-primary, input[type='submit']")
    submit_btn.click()

    # Wait for login success
    time.sleep(5)  # Extra wait for proxy/auth
    current_url = driver.current_url.lower()
    if "signin" in current_url or "login" in current_url:
        raise Exception("Login failed - credentials or geo-restriction issue.")
    print("Login successful.")

    # Step 2: Navigate to live streams
    print(f"Navigating to ICC Live: {stream_url}")
    driver.get(stream_url)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("ICC Live page loaded.")

    # Click play or live match if available (for today's India vs Australia semi-final)
    try:
        play_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='play'], .play-button, [data-testid='play'], .video-play")))
        play_btn.click()
        time.sleep(10)  # Longer wait to let stream init during live match
        print("Triggered play button.")
    except TimeoutException:
        print("No play button found - scanning for streams anyway.")
        # Fallback: Execute JS to play video if present
        driver.execute_script("if (document.querySelector('video')) { document.querySelector('video').play(); }")

    # Step 3: Extract m3u8 from network logs
    logs = driver.get_log('performance')
    for entry in logs:
        message = json.loads(entry['message'])['message']
        if message['method'] == 'Network.responseReceived':
            url = message['params']['response']['url']
            if re.search(r'\.m3u8(\?.*)?$', url) and ('icc' in url.lower() or 'live' in url.lower() or 'hls' in url.lower() or 'women' in url.lower()):
                # Dedupe
                if url not in streams:
                    streams.append(url)
                    print(f"Found stream: {url}")

    if not streams:
        print("No m3u8 from logs. Trying video src fallback...")
        try:
            video_elems = driver.find_elements(By.TAG_NAME, "video")
            for video in video_elems:
                src = video.get_attribute("src")
                if src and '.m3u8' in src:
                    if src not in streams:
                        streams.append(src)
                        print(f"Found video src: {src}")
        except Exception as ve:
            print(f"Video fallback error: {ve}")

except WebDriverException as e:
    print(f"WebDriverException (possible geo/proxy issue): {e}")
    print("Tips: Try a different proxy from PROXIES list or check event schedule.")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    if driver:
        driver.quit()

print(f"Extracted {len(streams)} valid streams.")

# Fallback to public sports M3U if no private streams (filtered for cricket/ICC/women's)
if not streams:
    print("No private streams found. Falling back to public sports M3U (may include cricket).")
    public_m3u_url = "https://iptv-org.github.io/iptv/categories/sports.m3u"  # IPTV-Org sports
    try:
        # Download and filter for cricket/ICC/women's
        import requests
        response = requests.get(public_m3u_url, timeout=10)
        if response.status_code == 200:
            lines = response.text.split('\n')
            filtered = []
            for i, line in enumerate(lines):
                if '#EXTINF' in line and any(keyword in line.lower() for keyword in ['cricket', 'icc', 'women', 'india', 'australia', 'world cup']):
                    filtered.append(line)
                    if i+1 < len(lines) and not lines[i+1].startswith('#'):
                        filtered.append(lines[i+1])
            if filtered:
                m3u_content = '#EXTM3U\n' + '\n'.join(filtered)
                streams = [line for line in filtered if line.startswith('http') and '.m3u8' in line]  # Extract URLs
                print(f"Filtered {len(streams)} relevant streams from public playlist.")
    except Exception as re:
        print(f"Public fallback error: {re}")

# Generate M3U content
m3u_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
if not streams:
    m3u_content += "# No live ICC TV streams available (check event schedule or proxy).\n"
else:
    for i, url in enumerate(streams, 1):
        title = f"ICC TV Live Stream {i} via {proxy['country']} Proxy"
        m3u_content += f"#EXTINF:-1 tvg-logo=\"ICC\" group-title=\"ICC TV Live\",{title}\n"
        m3u_content += f"{url}\n"

# Ensure exact filename
filename = "icc live.m3u"
with open(filename, 'w', encoding='utf-8') as f:
    f.write(m3u_content)

# Verify
if os.path.exists(filename) and os.path.getsize(filename) > 0:
    print(f"M3U file '{filename}' created with {len(streams)} streams.")
    with open(filename, 'r') as f:
        content = f.read()
        print("M3U preview:")
        print(content[:300] + "..." if len(content) > 300 else content)
else:
    print(f"Error: M3U file '{filename}' not created.")
    sys.exit(1)

print("Script completed successfully.")
