def main():
    if not os.getenv('ICC_USERNAME') or not os.getenv('ICC_PASSWORD'):
        raise Exception("Set ICC_USERNAME and ICC_PASSWORD environment variables.")
    
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable for GitHub (uncommented)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    stream_url = None
    try:
        login_to_icc(driver)
        match_url = find_live_match_url(driver)
        print(f"Live match URL: {match_url}")
        stream_url = get_m3u8_url(driver, match_url)  # Now handles m3u8 or mpd
        print(f"\nLive stream URL: {stream_url}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()
    
    # Generate Tivimate-compatible M3U if stream found
    if stream_url:
        # Dynamic channel name (e.g., from match URL or hardcode for today)
        channel_name = "ICC Live - IND-W vs AUS-W Semi-Final"  # Customize via match parsing if needed
        
        m3u_content = f"""#EXTM3U
#EXT-X-VERSION:3
#EXTINF:-1 tvg-id="ICC.Live" tvg-name="{channel_name}" group-title="Cricket",{channel_name}
{stream_url}
"""
        
        with open('icc_live.m3u', 'w') as f:
            f.write(m3u_content)
        print(f"\nTivimate-ready M3U saved: icc_live.m3u")
        print("Load in Tivimate: Playlists > Add > Local/Remote File")
    else:
        print("No live stream found—no M3U generated.")
