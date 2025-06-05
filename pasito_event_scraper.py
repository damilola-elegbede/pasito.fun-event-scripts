import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import argparse

# Configuration
BASE_PASITO_URL = "https://pasito.fun"

def get_page_content_with_browser(url):
    """Use Selenium to get fully rendered page content including dynamic elements"""
    print(f"🌐 Loading page with browser automation: {url}")
    
    # Setup Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = None
    try:
        # Initialize the Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # Load the page
        driver.get(url)
        
        # Wait for the page to fully load
        print("⏳ Waiting for page to fully render...")
        time.sleep(3)  # Give time for any dynamic content to load
        
        # Wait for specific elements that indicate the page is ready
        try:
            # Wait for either organizer section or venue section to be present
            WebDriverWait(driver, 10).until(
                lambda d: d.find_element(By.TAG_NAME, "body").text.strip() != ""
            )
        except Exception as e:
            print(f"⚠️  Warning: Timeout waiting for page elements: {e}")
        
        # Get the fully rendered page source
        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        print("✅ Page successfully loaded with browser automation")
        print(f"📄 Page source length: {len(page_source)} characters")
        print(f"📝 Visible text length: {len(page_text)} characters")
        
        return page_source, page_text
        
    except Exception as e:
        print(f"❌ Error loading page with browser automation: {e}")
        print("🔄 Falling back to requests.get()...")
        
        # Fallback to requests if Selenium fails
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text, response.text
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            return None, None
            
    finally:
        if driver:
            driver.quit()

def debug_dump_raw_html(raw_html, event_url):
    """Debug function to dump raw HTML for inspection"""
    print(f"\n{'='*80}")
    print(f"RAW HTML DEBUG DUMP")
    print(f"Event URL: {event_url}")
    print(f"{'='*80}")
    
    # Save full HTML to file for inspection
    filename = "debug_raw_html.html"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(raw_html)
        print(f"📄 Full raw HTML saved to: {filename}")
        print(f"   File size: {len(raw_html)} characters")
    except Exception as e:
        print(f"❌ Could not save HTML file: {e}")
    
    # Show key excerpts for venue detection
    print(f"\n🔍 SEARCHING FOR VENUE-RELATED CONTENT:")
    print(f"-" * 50)
    
    # Look for venue links (updated pattern for debug)
    venue_link_matches = re.findall(r'<a[^>]+href="(https://pasito\.fun/l/[^\"]+)"[^>]*>([^<]*)</a>', raw_html, re.IGNORECASE)
    if venue_link_matches:
        print(f"\n✅ Found {len(venue_link_matches)} venue link(s):")
        for i, match in enumerate(venue_link_matches):
            href, text = match
            clean_text = ' '.join(text.split())  # Clean whitespace
            print(f"   Link {i+1}: {href} → '{clean_text}'")
    else:
        print(f"\n❌ No venue links found")
    
    # Look for 📍 emoji
    pin_emoji_found = '📍' in raw_html
    print(f"\n📍 Emoji found in HTML: {pin_emoji_found}")
    if pin_emoji_found:
        # Find context around 📍
        pin_index = raw_html.find('📍')
        context_start = max(0, pin_index - 100)
        context_end = min(len(raw_html), pin_index + 200)
        context = raw_html[context_start:context_end]
        print(f"   Context around 📍: ...{context}...")
    
    # Look for organizer links
    organizer_matches = re.findall(r'<a[^>]*href="[^\"]*\/u\/[^\"]*"[^>]*>.*?</a>', raw_html, re.IGNORECASE)
    if organizer_matches:
        print(f"\n👥 Found {len(organizer_matches)} organizer links:")
        for i, match in enumerate(organizer_matches):
            print(f"   Organizer {i+1}: {match}")
    
    # Show section headings
    heading_matches = re.findall(r'<h[1-6][^>]*>.*?</h[1-6]>', raw_html, re.IGNORECASE)
    if heading_matches:
        print(f"\n📋 Found {len(heading_matches)} headings:")
        for i, match in enumerate(heading_matches[:10]):  # Show first 10
            print(f"   Heading {i+1}: {match}")
    
    print(f"\n{'='*80}")
    print(f"ANALYSIS COMPLETE - Check {filename} for full HTML content")
    print(f"{'='*80}")

def scrape_address_from_location_page(location_url, venue_name_from_link=None):
    """Use browser automation to get venue address from location page"""
    if not location_url: 
        return None
    
    print(f"🔍 Processing venue location...")
    print(f"Fetching venue details from: {location_url}")
    
    # Use browser automation to get fully rendered venue page content
    raw_html, page_text = get_page_content_with_browser(location_url)
    
    if not raw_html:
        print("❌ Failed to load venue page content")
        return None
    
    # Dump raw HTML for debugging
    debug_filename = "debug_location_raw_html.html"
    try:
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(raw_html)
        print(f"📄 Full raw HTML for location page saved to: {debug_filename}")
    except Exception as e:
        print(f"❌ Could not save location HTML file: {e}")
    
    # Parse with BeautifulSoup for structured extraction
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Extract venue name - use from link first, then try page
    venue_name = venue_name_from_link
    if not venue_name:
        title_tag = soup.find('title')
        if title_tag:
            venue_name = title_tag.get_text(strip=True)
        else:
            h1_tag = soup.find('h1')
            if h1_tag:
                venue_name = h1_tag.get_text(strip=True)
    
    # Look for the specific Address heading structure
    print("🔍 Looking for address under <h4> heading...")
    address_heading = soup.find('h4', class_='pc-h4 pc-heading--color pc-heading--margin', string='Address')
    
    street_address = ""
    city = ""
    state = ""
    zip_code = ""
    
    if address_heading:
        print("✅ Found Address heading")
        # Look for address content after the heading
        address_content = []
        
        # Get the next siblings after the Address heading
        current_element = address_heading.next_sibling
        while current_element:
            if hasattr(current_element, 'get_text'):
                text = current_element.get_text(strip=True)
                if text:
                    address_content.append(text)
            elif isinstance(current_element, str):
                text = current_element.strip()
                if text:
                    address_content.append(text)
            
            # Stop if we hit another heading
            if (hasattr(current_element, 'name') and 
                current_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                break
                
            current_element = current_element.next_sibling
            
            # Safety limit
            if len(address_content) > 10:
                break
        
        print(f"📍 Found address content: {address_content}")
        
        # Parse the address content
        if address_content:
            for line in address_content:
                # Check for street address pattern
                if re.search(r'\d+.*(?:street|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd|way|circle|cir|unit|#)', line, re.IGNORECASE):
                    street_address = line
                # Check for city, state zip pattern
                elif re.search(r'^[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}', line):
                    parts = line.split(',')
                    if len(parts) >= 2:
                        city = parts[0].strip()
                        state_zip_part = parts[1].strip().split()
                        if state_zip_part:
                            state = state_zip_part[0]
                            if len(state_zip_part) > 1:
                                zip_code = state_zip_part[1]
    
    # FALLBACK: Look for <address> tag
    if not street_address:
        print("🔄 Looking for <address> tag...")
        address_tag = soup.find('address')
        if address_tag:
            print("✅ Found <address> tag")
            p_tags = address_tag.find_all('p')
            if p_tags:
                for p in p_tags:
                    text = p.get_text(strip=True)
                    if re.search(r'\d+.*(?:street|avenue|ave|road|rd|lane|ln|drive|dr|boulevard|blvd|way|circle|cir|unit|#)', text, re.IGNORECASE):
                        street_address = text
                    elif re.search(r'^[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}', text):
                        parts = text.split(',')
                        if len(parts) >= 2:
                            city = parts[0].strip()
                            state_zip_part = parts[1].strip().split()
                            if state_zip_part:
                                state = state_zip_part[0]
                                if len(state_zip_part) > 1:
                                    zip_code = state_zip_part[1]
    
    # FALLBACK: Use regex on raw HTML to find address pattern
    if not street_address:
        print("🔄 Trying regex patterns on raw HTML...")
        
        # Look for address patterns in raw HTML
        address_patterns = [
            r'(\d+[^,\n]+(?:avenue|ave|street|st|road|rd|lane|ln|drive|dr|boulevard|blvd|way|circle|cir)[^,\n]*),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})',
            r'(\d+[^<>\n]+(?:avenue|ave|street|st|road|rd|lane|ln|drive|dr|boulevard|blvd|way|circle|cir)[^<>\n]*),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})'
        ]
        found = False
        for pattern in address_patterns:
            matches = re.findall(pattern, raw_html, re.IGNORECASE)
            if matches:
                match = matches[0]
                street_address = match[0].strip()
                city = match[1].strip()
                state = match[2].strip()
                zip_code = match[3].strip()
                print(f"📍 Found address via regex: {street_address}, {city}, {state} {zip_code}")
                found = True
                break
        # If still not found, try a generic US address pattern anywhere in the HTML
        if not found:
            print("🔄 Trying generic US address pattern on all visible text...")
            generic_pattern = r'(\d+\s+[\w\s\.]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})'
            generic_matches = re.findall(generic_pattern, page_text)
            if generic_matches:
                full_address = generic_matches[0]
                print(f"📍 Found generic address: {full_address}")
                # Try to split into components
                addr_parts = re.match(r'(\d+\s+[\w\s\.]+),\s*([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})', full_address)
                if addr_parts:
                    street_address = addr_parts.group(1).strip()
                    city = addr_parts.group(2).strip()
                    state = addr_parts.group(3).strip()
                    zip_code = addr_parts.group(4).strip()
    
    # Only create location object if we have real address data
    if street_address and city and state:
        location = {
            "is_online": False,
            "place": {
                "name": venue_name or "Venue",
                "location": {
                    "street": street_address,
                    "city": city,
                    "state": state,
                    "zip": zip_code,
                    "country": "US"
                }
            }
        }
        
        print(f"✅ Successfully extracted venue: {venue_name}")
        print(f"   Address: {street_address}")
        print(f"   City: {city}, {state} {zip_code}")
        return location
    else:
        print("⚠️  Could not extract complete address from venue page.")
        if street_address:
            print(f"   Found partial street: {street_address}")
        if city or state:
            print(f"   Found partial location: {city}, {state}")
        
        # Return venue name only without made-up address
        if venue_name:
            location = {
                "is_online": False,
                "place": {
                    "name": venue_name,
                    "location": {
                        "street": "",
                        "city": "",
                        "state": "",
                        "zip": "",
                        "country": "US"
                    }
                }
            }
            print(f"✅ Returning venue name only: {venue_name}")
            return location
        
        return None

def scrape_pasito_event(event_url, debug_mode=False):
    """Enhanced scraper using browser automation for complete content rendering"""
    print(f"\n{'='*60}")
    print(f"Processing Event: {event_url}")
    print(f"{'='*60}")
    
    # Use browser automation to get fully rendered content
    raw_html, page_text = get_page_content_with_browser(event_url)
    
    if not raw_html:
        print("❌ Failed to load page content")
        return None
    
    # DEBUG MODE: Dump raw HTML for inspection
    if debug_mode:
        debug_dump_raw_html(raw_html, event_url)
    
    # Parse with BeautifulSoup for structured extraction
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Extract basic event information
    title_tag = soup.find('title')
    event_name = title_tag.get_text(strip=True) if title_tag else "Unknown Event"
    
    # Look for description/content
    description = ""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        description = meta_desc['content']
    else:
        # Fallback to first paragraph or content
        content_paragraphs = soup.find_all('p')
        if content_paragraphs:
            description = ' '.join([p.get_text(strip=True) for p in content_paragraphs[:3]])
    
    print(f"📝 Event Name: {event_name}")
    print(f"📄 Description: {description[:100]}...")
    
    # Venue location detection - match exact Pasito.fun format
    print("\n🔍 Searching for /l/ venue links in fully rendered content...")
    
    location_url = None
    venue_name_from_link = None
    
    # Regex pattern to match Pasito.fun venue links with data-phx attributes
    print("🎯 Searching for Pasito.fun venue links...")
    pattern = r'<a[^>]+href="(https://pasito\.fun/l/[^\"]+)"[^>]*>([^<]*)</a>'
    
    matches = re.findall(pattern, raw_html, re.IGNORECASE | re.DOTALL)
    if matches:
        print(f"✅ Found {len(matches)} venue link(s):")
        for i, match in enumerate(matches):
            href, text = match[0], match[1]
            # Clean up the venue name (remove extra whitespace)
            clean_venue_name = ' '.join(text.split())
            print(f"   Link {i+1}: {href} → '{clean_venue_name}'")
        
        # Use the first match
        location_url = matches[0][0]
        venue_name_from_link = ' '.join(matches[0][1].split())  # Clean whitespace
        print(f"🔗 Selected venue: {location_url}")
        print(f"🏢 Venue name: '{venue_name_from_link}'")
    else:
        print("⚠️  No venue links found")

    if not location_url:
        print("⚠️  No /l/ venue links found")
        
        # Debug: Show all href links found
        all_href_pattern = r'href=["\']*([^"\'>\s]+)["\']*'
        all_hrefs = re.findall(all_href_pattern, raw_html, re.IGNORECASE)
        l_hrefs = [href for href in all_hrefs if '/l/' in href]
        
        if l_hrefs:
            print(f"🔍 DEBUG: Found {len(l_hrefs)} href(s) containing '/l/':")
            for href in l_hrefs[:5]:  # Show first 5
                print(f"   {href}")
        else:
            print("🔍 DEBUG: No hrefs containing '/l/' found at all")
    
    # Look for organizer link as backup
    organizer_url = None
    organizer_name = None
    
    if not location_url:
        organizer_pattern = r'<a[^>]+href="(/u/[^\"]+)"[^>]*>([^<]*)</a>'
        organizer_matches = re.findall(organizer_pattern, raw_html, re.IGNORECASE)
        
        if organizer_matches:
            org_href, org_text = organizer_matches[0]
            organizer_url = BASE_PASITO_URL + org_href
            organizer_name = org_text.strip()
            print(f"🔍 Found organizer link: {organizer_url} → '{organizer_name}'")
            print("📍 Will check organizer profile for venue information...")

        # Extract location from organizer
        if organizer_url:
            # Get organizer page content
            org_raw_html, org_page_text = get_page_content_with_browser(organizer_url)
            
            if org_raw_html:
                org_soup = BeautifulSoup(org_raw_html, 'html.parser')
                
                # Look for location info on organizer page
                location_text = None
                location_spans = org_soup.find_all('span', string=re.compile(r'.*,\s*[A-Z]{2}.*'))
                if location_spans:
                    location_text = location_spans[0].get_text(strip=True)
                
                if location_text and re.search(r'[A-Za-z\s]+,\s*[A-Z]{2}', location_text):
                    parts = location_text.split(',')
                    if len(parts) >= 2:
                        city = parts[0].strip()
                        state_part = parts[1].strip().split()[0] if parts[1].strip() else ""
                        
                        location_url = organizer_url
                        venue_name_from_link = organizer_name
                        
                        print(f"📍 Extracted organizer location: {organizer_name} in {city}, {state_part}")

    # Fetch and parse venue/organizer location
    location_data = None
    if location_url:
        location_data = scrape_address_from_location_page(location_url, venue_name_from_link)
    
    # Extract time information (simplified for now)
    event_time = None
    datetime_pattern = r'(\w{3},\s*\w{3}\s*\d{1,2}\s*\d{1,2}:\d{2}\s*[AP]M)'
    time_matches = re.findall(datetime_pattern, raw_html)
    if time_matches:
        event_time = time_matches[0]
        print(f"⏰ Found event time: {event_time}")

    # Build the event data structure
    event_data = {
        "name": event_name,
        "description": description[:500] if description else "",
        "cover_url": "https://pasito.fun/static/images/og-image.png",
        "is_online": False
    }
    
    # Add location data if available
    if location_data:
        event_data.update(location_data)
    else:
        # Fallback - basic event without specific venue
        event_data["place"] = {
            "name": "Dance Event",
            "location": {
                "street": "",
                "city": "Boulder",
                "state": "CO", 
                "zip": "",
                "country": "US"
            }
        }

    return event_data

def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(description='Scrape event data from pasito.fun')
    parser.add_argument('-e', '--events', nargs='+', help='URL(s) of the event(s) to scrape')
    parser.add_argument('-c', '--cover_image', help='URL of the cover image for the event')
    args = parser.parse_args()

    if args.events:
        event_urls = []
        for event in args.events:
            if event.startswith('@'):
                event = event[1:]  # Remove the @ symbol
            if not event.startswith('https://'):
                event = f"https://pasito.fun/e/{event}"  # Construct the full URL
            event_urls.append(event)
    else:
        event_urls = [
            "https://pasito.fun/e/boulder-salsa-bachata-rueda-wc-swing-social-e6sqn",
            "https://pasito.fun/e/salsa-bachata-sundays-at-la-rumba-289dc",
            "https://pasito.fun/e/salsa-bachata-sundays-at-la-rumba-289dc"
        ]

    print("PASITO.FUN EVENT SCRAPER WITH BROWSER AUTOMATION")
    print("=" * 60)
    print("\n🎯 Processing Event 1/1...")
    print("🔍 DEBUG MODE ENABLED - Will dump raw HTML")
    print("\n" + "=" * 60)

    for i, event_url in enumerate(event_urls, 1):
        print(f"\nProcessing Event: {event_url}")
        print("=" * 60)
        
        # Get page content with browser automation
        raw_html, page_text = get_page_content_with_browser(event_url)
        
        if not raw_html:
            print("❌ Failed to load page content")
            continue
        
        # Save raw HTML for debugging
        debug_filename = "debug_raw_html.html"
        try:
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(raw_html)
            print(f"📄 Full raw HTML saved to: {debug_filename}")
            print(f"   File size: {len(raw_html)} characters")
        except Exception as e:
            print(f"❌ Could not save HTML file: {e}")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Extract event name
        title_tag = soup.find('title')
        event_name = title_tag.get_text(strip=True) if title_tag else "Unknown Event"
        print(f"\n📝 Event Name: {event_name}")
        
        # Extract description
        description = ""
        description_tag = soup.find('meta', property='og:description')
        if description_tag:
            description = description_tag.get('content', '')
        print(f"📄 Description: {description}")
        
        # Extract venue
        venue = None
        venue_link = soup.find('a', href=re.compile(r'/l/'))
        if venue_link:
            venue_url = venue_link['href']
            venue_name = venue_link.get_text(strip=True)
            venue = scrape_address_from_location_page(venue_url, venue_name)
        
        # Extract event time
        event_time = ""
        time_tag = soup.find('time')
        if time_tag:
            event_time = time_tag.get_text(strip=True)
        print(f"⏰ Found event time: {event_time}")
        
        # Extract cover image
        cover_url = args.cover_image if args.cover_image else None
        
        # Create Facebook API JSON
        facebook_api_json = {
            "name": event_name,
            "description": description,
            "cover_url": cover_url,
            "is_online": False,
            "place": venue
        }
        
        print("\n📋 Facebook API JSON:")
        print(json.dumps(facebook_api_json, indent=2))
        
        print("\n" + "-" * 60)
        print("\n✅ Processing complete!")

if __name__ == "__main__":
    main() 