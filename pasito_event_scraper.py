import requests
from bs4 import BeautifulSoup
import json
import re
import time
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import pytz
from selenium.common.exceptions import TimeoutException

# Configuration
BASE_PASITO_URL = "https://pasito.fun"

class BrowserSession:
    """Manages a single browser session for reuse across multiple requests"""
    
    def __init__(self):
        self.driver = None
        self._setup_browser()
    
    def _setup_browser(self):
        """Initialize Chrome browser with optimized settings"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-images")  # Speed optimization
        chrome_options.add_argument("--disable-css")     # Speed optimization
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("✅ Browser session initialized")
        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}")
            self.driver = None
    
    def get_page_content(self, url):
        """Get fully rendered page content using the shared browser session"""
        if not self.driver:
            print("❌ Browser not available, falling back to requests")
            return self._fallback_request(url)
        
        try:
            print(f"🌐 Loading page: {url}")
            self.driver.get(url)
            
            # Wait for body to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            time.sleep(2)  # Brief wait for dynamic content
            
            page_source = self.driver.page_source
            print(f"✅ Page loaded ({len(page_source)} chars)")
            return page_source
            
        except Exception as e:
            print(f"❌ Browser error: {e}")
            return self._fallback_request(url)
    
    def _fallback_request(self, url):
        """Fallback to simple HTTP request if browser fails"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"❌ Fallback request failed: {e}")
            return None
    
    def close(self):
        """Clean up browser resources"""
        if self.driver:
            self.driver.quit()
            print("🔒 Browser session closed")

def extract_event_data(html_content, event_url, debug_mode=False):
    """Comprehensive event data extraction from HTML content"""
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Debug HTML dump if requested
    if debug_mode:
        with open('debug_event.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"📄 Debug HTML saved to debug_event.html")
    
    # Extract event name
    event_name = "Unknown Event"
    title_tag = soup.find('title')
    if title_tag and title_tag.get_text():
        event_name = title_tag.get_text().replace(' · Pasito', '').strip()
    else:
        h3_tag = soup.find('h3', class_='pc-h3')
        if h3_tag:
            event_name = h3_tag.get_text(strip=True)
    
    # Extract description
    description = ""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        description = meta_desc['content']
    else:
        prose_elem = soup.select_one('.prose')
        if prose_elem:
            description = prose_elem.get_text().strip()
    
    # Extract venue information
    venue_data = extract_venue_info(html_content, soup)
    
    # Extract time information
    start_time, end_time = extract_event_times(soup)
    
    # Build comprehensive event data
    event_data = {
        "name": event_name,
        "description": description[:500] if description else "",
        "cover_url": "https://pasito.fun/static/images/og-image.png",
        "is_online": False,
        "start_time": parse_time_to_iso8601(start_time) if start_time else "",
        "end_time": parse_time_to_iso8601(end_time, start_time) if end_time else ""
    }
    
    # Add venue data
    event_data.update(venue_data)
    
    return event_data

def extract_venue_info(html_content, soup):
    """Extract venue information from event page"""
    # Look for venue links
    venue_pattern = r'<a[^>]+href="(https://pasito\.fun/l/[^\"]+)"[^>]*>([^<]*)</a>'
    matches = re.findall(venue_pattern, html_content, re.IGNORECASE)
    
    if matches:
        venue_url = matches[0][0]
        venue_name = ' '.join(matches[0][1].split())
        print(f"🏢 Found venue: {venue_name}")
        return {"place": venue_name}
    
    # Fallback to basic location
    return {
        "place": {
            "name": "Dance Event",
            "location": {
                "city": "Boulder",
                "state": "CO",
                "country": "US"
            }
        }
    }

def extract_event_times(soup):
    """Extract start and end times from event page"""
    start_time = ""
    end_time = ""
    
    # Look for time information with clock emoji
    time_p = soup.find('p', class_='pc-text pc-p--margin', string=lambda s: s and '🕘' in s)
    if time_p:
        time_text = time_p.get_text(strip=True).replace('🕘', '').strip()
        print(f"🕘 Raw time text: {time_text}")
        
        # Handle different time formats
        # Format 1: "Thu, Jun 19 6:30 PM — 11:00 PM" (with em dash)
        if '—' in time_text:
            start_time = time_text.split('—')[0].strip()
            end_time = time_text.split('—')[1].strip()
        # Format 2: "Thu, Jun 5 6:30 PM 11:00 PM" (space separated)
        elif re.search(r'(\w{3}, \w{3} \d{1,2} \d{1,2}:\d{2} [AP]M) (\d{1,2}:\d{2} [AP]M)', time_text):
            match = re.search(r'(\w{3}, \w{3} \d{1,2} \d{1,2}:\d{2} [AP]M) (\d{1,2}:\d{2} [AP]M)', time_text)
            start_time = match.group(1).strip()
            end_time_raw = match.group(2).strip()
            
            # For end time, extract date from start time and combine
            date_part = re.search(r'(\w{3}, \w{3} \d{1,2})', start_time)
            if date_part:
                end_time = f"{date_part.group(1)} {end_time_raw}"
        else:
            start_time = time_text
    
    print(f"⏰ Parsed start time: {start_time}")
    print(f"⏰ Parsed end time: {end_time}")
    
    return start_time, end_time

# Keep existing utility functions
def parse_time_to_iso8601(time_str, start_date=None):
    """Parse a time string like 'Thu, Jun 12 6:30 PM' into ISO 8601 format."""
    try:
        # Handle end times that only have time portion (e.g., "11:00 PM")
        if start_date and not re.search(r'[A-Za-z]{3},\s*[A-Za-z]{3}\s*\d{1,2}', time_str):
            # Extract date part from start_date and combine with end time
            date_match = re.search(r'(\w{3}, \w{3} \d{1,2})', start_date)
            if date_match:
                time_str = f"{date_match.group(1)} {time_str}"
        
        # Add current year explicitly to avoid deprecation warning
        current_year = datetime.now().year
        dt = datetime.strptime(f"{time_str} {current_year}", '%a, %b %d %I:%M %p %Y')
        
        mountain_tz = pytz.timezone('America/Denver')
        dt = mountain_tz.localize(dt)
        return dt.isoformat()
    except Exception as e:
        print(f"⚠️  Error parsing time '{time_str}': {e}")
        return time_str

def extract_series_id(series_url):
    """Extract series ID from a Pasito series URL or ID"""
    if not series_url:
        return None
    
    if series_url.startswith('@'):
        series_url = series_url[1:]
    
    if series_url.startswith('https://'):
        series_id = series_url.rstrip('/').split('/')[-1]
    else:
        series_id = series_url
    
    return series_id

def get_series_events(series_id, browser_session):
    """Get all events from a series page using shared browser session"""
    if not series_id:
        return []
    
    series_url = f"https://pasito.fun/es/{series_id}/events"
    print(f"🔍 Fetching events from series: {series_url}")
    
    html_content = browser_session.get_page_content(series_url)
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'lxml')
    event_links = soup.find_all('a', href=re.compile(r'/e/[a-zA-Z0-9-]+'))
    event_urls = set()
    
    for link in event_links:
        href = link.get('href')
        if href:
            if not href.startswith('https://'):
                href = f"https://pasito.fun{href}"
            event_urls.add(href)
    
    print(f"✅ Found {len(event_urls)} unique events in series")
    return list(event_urls)

def main():
    parser = argparse.ArgumentParser(description='Efficiently scrape Pasito events for Facebook')
    parser.add_argument('-e', '--events', nargs='+', help='Pasito event URLs to scrape')
    parser.add_argument('-s', '--series', help='Pasito series ID or link to scrape events from')
    parser.add_argument('-c', '--cover-image', help='URL of the cover image to use for Facebook events')
    parser.add_argument('-p', '--preview', action='store_true', help='Preview Facebook event call without making the call')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode with HTML dumps')
    args = parser.parse_args()

    if not args.events and not args.series:
        parser.error("Either -e/--events or -s/--series must be provided")

    # Initialize shared browser session
    browser = BrowserSession()
    
    try:
        # Collect all events to process
        events_to_process = []
        if args.series:
            series_id = extract_series_id(args.series)
            if not series_id:
                print("❌ Invalid series URL or ID")
                return
            events_to_process = get_series_events(series_id, browser)
        else:
            events_to_process = args.events

        # Process each event efficiently
        results = []
        for i, event_url in enumerate(events_to_process, 1):
            print(f"\n📝 Processing event {i}/{len(events_to_process)}: {event_url}")
            
            # Get page content using shared browser
            html_content = browser.get_page_content(event_url)
            if not html_content:
                print("❌ Failed to load page content")
                continue
            
            # Extract event data
            event_data = extract_event_data(html_content, event_url, args.debug)
            if not event_data:
                print("❌ Failed to extract event data")
                continue
            
            # Add cover image if provided
            if args.cover_image:
                event_data["cover_url"] = args.cover_image
            
            # Display results
            print(f"📌 Event: {event_data['name']}")
            print(f"⏰ Time: {event_data.get('start_time', 'TBD')}")
            print(f"📍 Venue: {event_data.get('place', 'TBD')}")
            
            if args.preview:
                print("\n📋 Facebook API JSON:")
                print(json.dumps(event_data, indent=2))
                print("-" * 60)
            
            results.append(event_data)
        
        print(f"\n✅ Successfully processed {len(results)} events")
        
        if not args.preview and results:
            print("🔄 TODO: Implement Facebook event creation logic")
            
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        # Clean up browser resources
        browser.close()

if __name__ == "__main__":
    main()