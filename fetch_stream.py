import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

# Debug print to confirm script start
print("Starting fetch_stream.py - Fetching ICC live streams...")

# Set up Chrome options for headless mode in CI
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

try:
    driver = webdriver.Chrome(options=chrome_options)
    print("Chrome driver initialized successfully.")
except Exception as e:
    print(f"Error initializing Chrome driver: {e}")
    sys.exit(1)

# Example: Scrape from a cricket stream site (REPLACE WITH ACTUAL SITE/LOGIC)
# Note: Ensure compliance with ToS; this is a placeholder for ICC live streams
url = "https://example-cricket-stream-site.com/live"  # Replace with real URL, e.g., cricbuzz or similar
driver.get(url)

try:
    # Wait for stream elements (customize selectors based on site)
    wait = WebDriverWait(driver, 10)
    stream_elements = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".stream-link"))  # Adjust selector
    )
    print(f"Found {len(stream_elements)} stream elements.")
except TimeoutException:
    print("No stream elements found within timeout. No live ICC streams available?")
    stream_elements = []

streams = []
for elem in stream_elements:
    try:
        title = elem.find_element(By.CSS_SELECTOR, ".title").text  # Adjust
        stream_url = elem.get_attribute("href") or elem.find_element(By.TAG_NAME, "a").get_attribute("href")
        if stream_url:
            streams.append((title, stream_url))
    except NoSuchElementException:
        continue

print(f"Extracted {len(streams)} valid streams.")

# Generate M3U content
m3u_content = "#EXTM3U\n"
for title, url in streams:
    m3u_content += f"#EXTINF:-1,{title}\n"
    m3u_content += f"{url}\n"

# Ensure exact filename with space for workflow compatibility
filename = "icc live.m3u"
with open(filename, 'w', encoding='utf-8') as f:
    f.write(m3u_content)

# Verify file creation
if os.path.exists(filename) and os.path.getsize(filename) > 0:
    print(f"M3U file '{filename}' created successfully with {len(streams)} streams.")
    with open(filename, 'r') as f:
        print("M3U preview (first 200 chars):")
        print(f.read(200) + "..." if len(f.read()) > 200 else f.read())
else:
    print(f"Error: M3U file '{filename}' not created or empty.")
    sys.exit(1)

driver.quit()
print("Script completed successfully.")
