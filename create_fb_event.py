"""
Facebook Event Creator for Pasito Events

This script creates Facebook events from Pasito event pages. It can process individual events
or entire series of events.

Setup:
1. Install dependencies:
   pip install -r requirements.txt

2. Set environment variables:
   - FB_PAGE_ID: Your Facebook Page ID
   - FB_PAGE_ACCESS_TOKEN: Your Facebook Page Access Token
   
   You can set these in your shell:
   export FB_PAGE_ID="your_page_id"
   export FB_PAGE_ACCESS_TOKEN="your_access_token"
   
   Or create a .env file with these variables.

Usage:
1. Process a single event:
   python create_fb_event.py <event_id> [--preview]
   
   Example:
   python create_fb_event.py blue-ice-bachata-night-r14by --preview

2. Process all events in a series:
   python create_fb_event.py --series <series_id> [--preview]
   
   Example:
   python create_fb_event.py --series boulder-salsa-bachata-rueda-wc-swing-social-xd9r4 --preview

Options:
  --preview    Preview the Facebook API payload without creating the event
  --series     Process all events from a series

Features:
- Automatically scrapes event details from Pasito
- Handles location details and venue information
- Translates non-English descriptions to English
- Adds source link to the event description
- Supports both single events and series
- Preview mode for testing without creating events

Note: The script requires a Facebook Page Access Token with the following permissions:
- pages_manage_events
- pages_read_engagement
"""

import requests
import os
import json
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta
import pytz
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# --- CONFIGURATION ---
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GRAPH_API_VERSION = "v20.0"
BASE_PASITO_URL = "https://pasito.fun"

def setup_webdriver():
    """Set up and return a configured Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def upload_photo_for_event(image_path):
    """Uploads a local photo to the Page's photos without publishing it."""
    if not Path(image_path).is_file():
        print(f" Error: Cover image file not found at '{image_path}'")
        return None
    print(f" Uploading cover image from {image_path}...")
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"
    params = {"published": "false", "access_token": FB_PAGE_ACCESS_TOKEN}
    files = {'source': open(image_path, 'rb')}
    try:
        response = requests.post(url, params=params, files=files)
        response.raise_for_status()
        result = response.json()
        print(f" Successfully uploaded photo. Photo ID: {result['id']}")
        return result['id']
    except requests.RequestException as e:
        print(f"\n❌ Error: Failed to upload photo. Status Code: {e.response.status_code}, Response: {e.response.text}")
        return None

def scrape_series_for_event_ids(series_id):
    """Scrapes a series page for event IDs."""
    url = f"{BASE_PASITO_URL}/es/{series_id}"
    print(f"\nScraping series page {url}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        event_links = soup.select('a[href^="/e/"]')
        event_ids = [link['href'].replace('/e/', '') for link in event_links]
        print(f"Found {len(event_ids)} events: {', '.join(event_ids)}")
        return event_ids
    except requests.RequestException as e:
        print(f"Error: Could not fetch series page {series_id}. {e}")
        return []

def find_location_links(soup):
    """Find location page links in the HTML and return the URL and venue name."""
    try:
        # Look for links that contain /l/ in their href (both relative and absolute URLs)
        location_links = soup.find_all('a', href=re.compile(r'/l/'))
        
        if location_links:
            for link in location_links:
                href = link['href']
                # Handle both relative and absolute URLs
                location_url = href if href.startswith('http') else BASE_PASITO_URL + href
                venue_name = link.get_text(strip=True)
                print(f"🔗 Found location link: {location_url} → '{venue_name}'")
                return location_url, venue_name
        
        # Alternative: look for links that contain location-related keywords
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True)
            
            # Check if this might be a location link based on text content
            if any(keyword in text.lower() for keyword in ['venue', 'location', 'address', 'ballroom', 'hall']) and href.startswith('/'):
                location_url = BASE_PASITO_URL + href
                print(f"🔗 Found potential location link: {location_url} → '{text}'")
                return location_url, text
        
        print("⚠️  No location links found in page")
        return None, None
        
    except Exception as e:
        print(f"❌ Error searching for location links: {e}")
        return None, None

def get_manual_location_input(venue_name):
    """Prompts user for manual location input."""
    print(f"\n📍 Please provide location details for: {venue_name}")
    
    is_online = input("- Is this an online event? (y/n): ").lower() == 'y'
    location_details = {
        "is_online": is_online,
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
    
    if not is_online:
        location_details["place"]["location"].update({
            "street": input("  - Street Address: ").strip(),
            "city": input("  - City: ").strip(),
            "state": input("  - State (2-letter code): ").strip().upper(),
            "zip": input("  - ZIP Code: ").strip(),
        })
    
    return location_details

def scrape_address_from_location_page(location_url, venue_name):
    """Scrapes address details from a location page using Selenium."""
    print(f"\n🔍 Scraping location details from: {location_url}")
    
    driver = None
    try:
        driver = setup_webdriver()
        driver.get(location_url)
        
        # Wait for the main content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(2)
        
        # Get the page source after JavaScript has executed
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Initialize location details
        location_details = {
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
        
        # Extract address from the page
        page_text = soup.get_text()
        
        # Look for address patterns
        # Pattern 1: City, State ZIP
        city_state_zip_pattern = r'([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})'
        city_state_zip_match = re.search(city_state_zip_pattern, page_text)
        
        if city_state_zip_match:
            city, state, zip_code = city_state_zip_match.groups()
            location_details["place"]["location"].update({
                "city": city.strip(),
                "state": state.strip(),
                "zip": zip_code.strip()
            })
            print(f"✅ Found city/state/zip: {city}, {state} {zip_code}")
        
        # Pattern 2: Street address
        street_pattern = r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Place|Pl|Court|Ct|Circle|Cir|Way|Terrace|Ter|Trail|Trl))'
        street_match = re.search(street_pattern, page_text, re.IGNORECASE)
        
        if street_match:
            street = street_match.group(1).strip()
            location_details["place"]["location"]["street"] = street
            print(f"✅ Found street address: {street}")
        
        # Check if it's an online event
        online_keywords = ['online', 'virtual', 'zoom', 'webinar', 'streaming']
        if any(keyword in page_text.lower() for keyword in online_keywords):
            location_details["is_online"] = True
            print("ℹ️  Detected as online event")
        
        # Validate that we found at least some location details
        if not any(location_details["place"]["location"].values()):
            print("⚠️  Could not find complete address details from location page")
            print("🔄 Falling back to manual location input...")
            return get_manual_location_input(venue_name)
            
        return location_details
        
    except Exception as e:
        print(f"❌ Error: Failed to parse location details. {e}")
        print("🔄 Falling back to manual location input...")
        return get_manual_location_input(venue_name)
    finally:
        if driver:
            driver.quit()

def extract_location_from_text(soup):
    """Extracts location information from the page text."""
    try:
        page_text = soup.get_text()
        lines = page_text.split('\n')
        
        # Look for "City, State" pattern that appears after "Series" or as standalone
        location_city = None
        location_state = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for city, state pattern
            location_match = re.match(r'^([A-Za-z\s]+),\s*([A-Z]{2})', line)
            if location_match:
                city, state = location_match.groups()
                city = city.strip()
                # Make sure it's a reasonable city name
                if len(city) > 2 and not any(word in city.lower() for word in ['series', 'organizer', 'social']):
                    location_city = city
                    location_state = state
                    break
        
        if location_city and location_state:
            location = {
                "is_online": False,
                "place": {
                    "name": f"{location_city}, {location_state}",
                    "location": {
                        "street": "",
                        "city": location_city,
                        "state": location_state,
                        "zip": "",
                        "country": "US"
                    }
                }
            }
            print(f"Extracted location: {location_city}, {location_state}")
            return location
    except Exception as e:
        print(f"Error extracting location: {e}")
    
    return None

def clean_description(text):
    """Clean up the description by removing header/footer text and extra whitespace."""
    if not text:
        return ""
    
    # Split into lines and remove empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Find the start of the actual description (after any header text)
    start_idx = 0
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['every', 'join us', 'welcome', 'about']):
            start_idx = i
            break
    
    # Find the end of the actual description (before any footer text)
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['website', 'register', 'sign in', 'open options', 'blog']):
            end_idx = i
            break
    
    # Get the cleaned description
    cleaned_lines = lines[start_idx:end_idx]
    
    # If we didn't find any content, use the original text
    if not cleaned_lines:
        cleaned_lines = lines
    
    # Join lines and clean up extra whitespace
    cleaned_text = ' '.join(cleaned_lines)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    # Remove any remaining header/footer text
    cleaned_text = re.sub(r'^.*?(?=Every|Join|Welcome|About)', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'(Website|Register|Sign in|Open options|Blog).*$', '', cleaned_text, flags=re.IGNORECASE)
    
    return cleaned_text.strip()

def clean_city(city_text):
    """Extract only the city name (last word) from the city field."""
    if not city_text:
        return ""
    # Remove any non-letter characters and extra whitespace
    city_text = re.sub(r'[^A-Za-z\s]', '', city_text)
    city_text = re.sub(r'\s+', ' ', city_text).strip()
    # Take the last word as the city name
    city_name = city_text.split()[-1] if city_text.split() else city_text
    return city_name

def scrape_pasito_event(event_id):
    """Scrapes the main event page for all relevant details using Selenium."""
    url = f"{BASE_PASITO_URL}/e/{event_id}"
    print(f"Scraping event page: {url}...")
    
    driver = None
    try:
        driver = setup_webdriver()
        driver.get(url)
        
        # Wait for the main content to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(2)
        
        # Get the page source after JavaScript has executed
        page_source = driver.page_source
        
        # Save raw HTML to file
        with open('raw.txt', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("Saved raw HTML to raw.txt")
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract title from title tag
        name = ""
        title_tag = soup.find('title')
        if title_tag:
            name = title_tag.get_text(strip=True)
        
        # Extract description - look for the main content before organizer info
        page_text = soup.get_text()
        
        # Find the event title in the page text to use as a split point
        lines = page_text.split('\n')
        desc_lines = []
        found_title = False
        
        # Look for the actual event title in the page (usually appears after initial description)
        event_title_in_page = None
        for i, line in enumerate(lines):
            line = line.strip()
            if line and '🕘' in lines[i+1:i+3] if i+1 < len(lines) else False:
                event_title_in_page = line
                break
        
        # Extract description: everything before the event title that appears before the time
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Stop at time marker, organizer, or the event title that appears before time
            if '🕘' in line or line.lower() == 'organizer' or line.lower() == 'series':
                break
            if event_title_in_page and line == event_title_in_page:
                break
            desc_lines.append(line)
        
        description = clean_description(' '.join(desc_lines))
        
        # If we found an event title in the page, use that instead of the HTML title
        if event_title_in_page:
            name = event_title_in_page
        
        # Extract time information
        scraped_time = None
        time_pattern = r'🕘[^🕘]*?(\d{1,2}:\d{2}\s*[AP]M)\s*[—–-]\s*(\d{1,2}:\d{2}\s*[AP]M)'
        time_match = re.search(time_pattern, page_text)
        if time_match:
            start_time, end_time = time_match.groups()
            scraped_time = f"{start_time} - {end_time}"
            print(f"Found schedule on page: {scraped_time}")
        
        # Extract date information
        scraped_date = None
        date_pattern = r'🕘[^🕘]*?([A-Za-z]{3}),\s*([A-Za-z]{3})\s*(\d{1,2})'
        date_match = re.search(date_pattern, page_text)
        if date_match:
            day_of_week, month, day = date_match.groups()
            scraped_date = f"{month} {day}"
            print(f"Found date on page: {scraped_date}")
        
        # Extract location using improved approach
        print("\n🔍 Searching for venue location...")
        
        # First, try to find location page links
        location_url, venue_name_from_link = find_location_links(soup)
        location_details = None
        
        if location_url:
            # Found a location page link - fetch detailed address
            location_details = scrape_address_from_location_page(location_url, venue_name_from_link)
            if location_details and 'place' in location_details and 'location' in location_details['place']:
                # Clean up the city field
                location_details['place']['location']['city'] = clean_city(location_details['place']['location']['city'])
        
        if not location_details:
            # Fallback to text extraction
            print("🔄 Falling back to text-based location extraction...")
            location_details = extract_location_from_text(soup)
        
        print("Event page scraping successful.")
        return {
            "name": name,
            "description": description,
            "scraped_time": scraped_time,
            "scraped_date": scraped_date,
            "location_details": location_details
        }
    except Exception as e:
        print(f" Error: Could not fetch URL. {e}")
        return None
    finally:
        if driver:
            driver.quit()

def translate_description(text):
    if not text: return ""
    try:
        translator = GoogleTranslator(source='auto', target='en')
        translated = translator.translate(text)
        if translated != text:
            print("Translating description to English...")
        return translated
    except Exception as e:
        print(f"Warning: Could not translate text. Using original. Error: {e}")
        return text

def get_event_details_from_user(event_name, scraped_location_details, scraped_time, scraped_date, preview=False):
    """Get event details, using defaults in preview mode or exiting if data is missing."""
    print(f"\nProcessing event: \"{event_name}\"")
    
    start_time_obj, end_time_obj = None, None
    duration_hours = None

    if scraped_time:
        try:
            # Example: "7:00 PM - 12:30 AM"
            start_str, end_str = [t.strip() for t in scraped_time.split('-')]
            start_time_obj = datetime.strptime(start_str, "%I:%M %p")
            end_time_obj = datetime.strptime(end_str, "%I:%M %p")
            if end_time_obj < start_time_obj: # Handle overnight events
                end_time_obj += timedelta(days=1)
            duration_hours = (end_time_obj - start_time_obj).total_seconds() / 3600
            print(f"Found schedule on page: {scraped_time} ({duration_hours:.2f}-hour duration).")
        except ValueError:
            print("❌ Could not parse time from page.")
            if not preview:
                raise ValueError("Invalid time format in scraped data")

    # Get date input
    if scraped_date:
        try:
            current_year = datetime.now().year
            parsed_date = datetime.strptime(f"{scraped_date} {current_year}", "%b %d %Y")
            start_date_str = parsed_date.strftime("%Y-%m-%d")
            print(f"Using scraped date: {start_date_str}")
        except:
            print("❌ Could not parse date from page.")
            if not preview:
                raise ValueError("Invalid date format in scraped data")
            start_date_str = datetime.now().strftime("%Y-%m-%d")
            print(f"Using current date: {start_date_str}")
    else:
        if not preview:
            raise ValueError("No date found in scraped data")
        start_date_str = datetime.now().strftime("%Y-%m-%d")
        print(f"Using current date: {start_date_str}")
    
    if not start_time_obj:
        if not preview:
            raise ValueError("No start time found in scraped data")
        start_time_str = "19:00"  # Default to 7 PM
        print(f"Using default start time: {start_time_str}")
    if not duration_hours:
        if not preview:
            raise ValueError("Could not determine event duration")
        duration_hours = 3.0  # Default to 3 hours
        print(f"Using default duration: {duration_hours} hours")
    
    timezone_str = "America/Denver"
    print(f"Using timezone: {timezone_str}")
    
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        if not preview:
            raise ValueError(f"Invalid timezone: {timezone_str}")
        tz = pytz.timezone("America/Denver")
    
    start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
    final_start_time = start_time_obj.time() if start_time_obj else datetime.strptime(start_time_str, "%H:%M").time()
    
    start_datetime_local = tz.localize(datetime.combine(start_date_obj, final_start_time))
    end_datetime_local = start_datetime_local + timedelta(hours=duration_hours)
    
    start_time_utc = start_datetime_local.astimezone(pytz.utc).isoformat()
    end_time_utc = end_datetime_local.astimezone(pytz.utc).isoformat()
    
    final_details = {"start_time": start_time_utc, "end_time": end_time_utc, "event_time_zone": timezone_str}
    
    if scraped_location_details:
        final_details.update(scraped_location_details)
    else:
        if not preview:
            raise ValueError("No location details found in scraped data")
        # Use default location for preview
        final_details["is_online"] = False
        final_details["place"] = {
            "name": "Default Venue",
            "location": {
                "street": "123 Main St",
                "city": "Boulder",
                "state": "CO",
                "zip": "80301",
                "country": "US"
            }
        }
        print("Using default location for preview")

    return final_details

def create_facebook_event(event_data):
    """Create a Facebook event with the given data."""
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("❌ Error: Missing Facebook credentials. Cannot post event.")
        return None
        
    graph_api_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/events"
    headers = {'Content-Type': 'application/json'}
    params = {'access_token': FB_PAGE_ACCESS_TOKEN}
    print("Preparing to create Facebook event...")
    try:
        response = requests.post(graph_api_url, headers=headers, data=json.dumps(event_data), params=params)
        response.raise_for_status()
        result = response.json()
        print(f"\n✅ Success! Facebook event created: https://www.facebook.com/events/{result['id']}/")
        return result
    except requests.RequestException as e:
        print(f"\n❌ Error: Failed to create Facebook event. Status Code: {e.response.status_code}, Response: {e.response.text}")
        return None

def preview_facebook_payload(event_data):
    """Preview what will be sent to Facebook API"""
    preview_output = []
    preview_output.append("\n" + "="*80)
    preview_output.append("FACEBOOK EVENT API CALL PREVIEW")
    preview_output.append("="*80)
    preview_output.append("Endpoint: https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/events")
    preview_output.append("\nHeaders:")
    preview_output.append("  Content-Type: application/json")
    preview_output.append("\nParameters:")
    preview_output.append("  access_token: [FB_PAGE_ACCESS_TOKEN]")
    preview_output.append("\nRequest Body:")
    # Create a copy of the data to avoid modifying the original
    preview_data = event_data.copy()
    # Format the data for better readability
    formatted_data = json.dumps(preview_data, indent=2, default=str)
    preview_output.append(formatted_data)
    preview_output.append("\n" + "="*80)
    preview_output.append("Note: This is a preview. No event will be created.")
    preview_output.append("="*80)
    
    # Print to console
    print("\n".join(preview_output))
    
    # Save to file
    with open('facebook_api_preview.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(preview_output))
    print("\nSaved API preview to facebook_api_preview.txt")

def process_single_event(event_id, preview=False, clean=False):
    """Process a single event ID and create a Facebook event or preview payload."""
    print(f"\n{'='*50}")
    print(f"Processing event ID: {event_id}")
    print(f"{'='*50}")
    
    # Scrape event details from Pasito
    event_data = scrape_pasito_event(event_id)
    if not event_data:
        print(f"❌ Failed to scrape event {event_id}")
        return False
    
    # Check for required fields
    required_fields = ['name', 'description', 'location_details']
    missing_fields = [field for field in required_fields if not event_data.get(field)]
    if missing_fields:
        print(f"❌ Missing required fields: {', '.join(missing_fields)}")
        return False
    
    # Translate description if needed
    event_data['description'] = translate_description(event_data['description'])
    
    # Add Pasito event link to description
    pasito_event_link = f"{BASE_PASITO_URL}/e/{event_id}"
    event_data['description'] += f"\n\nThis event was created from {pasito_event_link}"
    
    # Get additional details from user
    try:
        event_data.update(get_event_details_from_user(
            event_data['name'],
            event_data.get('location_details'),
            event_data.get('scraped_time'),
            event_data.get('scraped_date'),
            preview=preview
        ))
    except Exception as e:
        print(f"❌ Error getting event details: {e}")
        return False
    
    # Remove cover_url as we're not handling it
    if 'cover_url' in event_data:
        del event_data['cover_url']
    
    # Preview the event data
    preview_facebook_payload(event_data)
    
    if preview:
        print("\n[PREVIEW MODE] No event will be created.")
        # Clean up temporary files if --clean flag is set
        if clean:
            for temp_file in ['raw.txt', 'facebook_api_preview.txt']:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    print(f"Warning: Could not remove temporary file {temp_file}: {e}")
        return True
    
    # Create the Facebook event
    result = create_facebook_event(event_data)
    if result:
        print(f"✅ Successfully created Facebook event for {event_id}")
        return True
    else:
        print(f"❌ Failed to create Facebook event for {event_id}")
        return False

def main():
    """Main function to handle multiple event IDs."""
    parser = argparse.ArgumentParser(description='Create Facebook events from Pasito event IDs')
    parser.add_argument('event_ids', nargs='*', help='One or more Pasito event IDs to process')
    parser.add_argument('-s', '--series', help='Series ID to scrape for event IDs')
    parser.add_argument('-p', '--preview', action='store_true', help='Preview API payload without creating events')
    parser.add_argument('-c', '--clean', action='store_true', help='Clean up temporary files after preview')
    args = parser.parse_args()
    
    # Check for required environment variables (skip if preview)
    if not args.preview and (not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN):
        print("❌ Error: FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN environment variables must be set")
        return
    
    # Get event IDs to process
    event_ids = []
    
    # If series ID is provided, scrape for event IDs
    if args.series:
        event_ids.extend(scrape_series_for_event_ids(args.series))
    
    # Add any explicitly provided event IDs
    event_ids.extend(args.event_ids)
    
    if not event_ids:
        print("❌ No event IDs to process")
        return
    
    # Process each event ID
    successful = 0
    failed = 0
    
    for event_id in event_ids:
        if process_single_event(event_id, preview=args.preview, clean=args.clean):
            successful += 1
        else:
            failed += 1
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Event Creation Summary:")
    print(f"Total events processed: {len(event_ids)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()