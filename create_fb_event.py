import requests
import os
import json
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from googletrans import Translator
from datetime import datetime, timedelta
import pytz
import re

# --- CONFIGURATION ---
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GRAPH_API_VERSION = "v20.0"
BASE_PASITO_URL = "https://pasito.fun"

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

def scrape_series_for_event_ids(series_id, prefix):
    """Scrapes a series page and filters for events with a specific prefix."""
    url = f"{BASE_PASITO_URL}/es/{series_id}"
    print(f"\n Scraping series page {url}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        event_links = soup.select('a[href^="/e/"]')
        all_event_ids = [link['href'].replace('/e/', '') for link in event_links]
        print(f" Found {len(all_event_ids)} total events. Filtering for prefix: '{prefix}'")
        filtered_ids = [eid for eid in all_event_ids if eid.startswith(prefix)]
        if not filtered_ids:
            print(f" Warning: No event IDs matched the prefix '{prefix}'.")
            return []
        print(f" Found {len(filtered_ids)} matching event IDs: {', '.join(filtered_ids)}")
        return filtered_ids
    except requests.RequestException as e:
        print(f" Error: Could not fetch series page {series_id}. {e}")
        return []

def find_location_links(soup):
    """Find location page links in the HTML and return the URL and venue name."""
    try:
        # Look for links that start with /l/
        location_links = soup.find_all('a', href=re.compile(r'^/l/'))
        
        if location_links:
            for link in location_links:
                location_url = BASE_PASITO_URL + link['href']
                venue_name = link.get_text(strip=True)
                print(f"🔗 Found location link: {location_url} → '{venue_name}'")
                return location_url, venue_name
        
        # Alternative: look for links that contain location-related keywords
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True)
            
            # Check if this might be a location link based on text content
            if any(keyword in text.lower() for keyword in ['venue', 'location', 'address']) and href.startswith('/'):
                location_url = BASE_PASITO_URL + href
                print(f"🔗 Found potential location link: {location_url} → '{text}'")
                return location_url, text
        
        print("⚠️  No location links found in page")
        return None, None
        
    except Exception as e:
        print(f"❌ Error searching for location links: {e}")
        return None, None
    """Extracts location information from the page text."""
    try:
        page_text = soup.get_text()
        lines = page_text.split('\n')
        
        # Look for "Boulder, CO" pattern that appears after "Series" or as standalone
        location_city = None
        location_state = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for city, state pattern
            location_match = re.match(r'^([A-Za-z\s]+),\s*([A-Z]{2})

def scrape_pasito_event(event_id):
    """Scrapes the main event page for all relevant details."""
    url = f"{BASE_PASITO_URL}/e/{event_id}"
    print(f"Scraping event page: {url}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
        
        description = ' '.join(desc_lines).strip()
        
        # If we found an event title in the page, use that instead of the HTML title
        if event_title_in_page:
            name = event_title_in_page
        
        # Extract cover image from meta tag
        cover_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            cover_url = og_image['content']
        
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
        
        if not location_details:
            # Fallback to text extraction
            print("🔄 Falling back to text-based location extraction...")
            location_details = extract_location_from_text(soup)
        
        print("Event page scraping successful.")
        return {
            "name": name,
            "description": description,
            "cover_url": cover_url,
            "scraped_time": scraped_time,
            "scraped_date": scraped_date,
            "location_details": location_details
        }
    except requests.RequestException as e:
        print(f" Error: Could not fetch URL. {e}")
        return None

def translate_description(text):
    if not text: return ""
    try:
        translator = Translator()
        detected = translator.detect(text)
        if detected.lang != 'en':
            print("Translating description to English...")
            return translator.translate(text, dest='en').text
        return text
    except Exception as e:
        print(f"Warning: Could not translate text. Using original. Error: {e}")
        return text

def get_event_details_from_user(event_name, scraped_location_details, scraped_time, scraped_date):
    """Prompts only for details that couldn't be scraped."""
    print(f"\nPlease provide the details for the event: \"{event_name}\"")
    
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
            print("Could not parse time from page.")

    # Get date input
    if scraped_date:
        start_date_str = input(f"- Event Start Date (YYYY-MM-DD) [Found: {scraped_date}]: ")
        if not start_date_str.strip():
            # Try to convert scraped date to full date
            try:
                current_year = datetime.now().year
                parsed_date = datetime.strptime(f"{scraped_date} {current_year}", "%b %d %Y")
                start_date_str = parsed_date.strftime("%Y-%m-%d")
                print(f"Using converted date: {start_date_str}")
            except:
                start_date_str = input("- Event Start Date (YYYY-MM-DD): ")
    else:
        start_date_str = input("- Event Start Date (YYYY-MM-DD): ")
    
    if not start_time_obj:
        start_time_str = input("- Event Start Time (HH:MM, 24-hour format): ")
    if not duration_hours:
        duration_hours = float(input("- Event duration in hours (e.g., 2.5): "))
        
    timezone_str = input(f"- Timezone [America/Denver]: ") or "America/Denver"
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
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
        print("Could not automatically determine location, please provide details manually:")
        is_online = input("- Is the event online? (y/n): ").lower() == 'y'
        final_details["is_online"] = is_online
        if not is_online:
            final_details["place"] = {
                "name": input("  - Venue Name: "), 
                "location": {
                    "street": input("  - Street: "), 
                    "city": input("  - City: "), 
                    "state": input("  - State: "), 
                    "zip": input("  - Zip: "), 
                    "country": "US"
                }
            }

    return final_details

def create_facebook_event(event_data, cover_photo_id=None):
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("Error: Missing Facebook credentials. Cannot post event.")
        return
    if cover_photo_id:
        event_data["cover"] = {"source": cover_photo_id}
        if "cover_url" in event_data: del event_data["cover_url"]
        print("Using local cover image for event.")
    else:
        print("Using scraped cover image for event.")
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
    print("\n" + "="*60)
    print("FACEBOOK EVENT PAYLOAD PREVIEW")
    print("="*60)
    print(json.dumps(event_data, indent=2, default=str))
    print("="*60)

def main():
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("Error: Missing required environment variables FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN.")
        return

    parser = argparse.ArgumentParser(description="Create Facebook events by scraping Pasito.fun pages.")
    parser.add_argument('-e', '--events', type=str, help='Comma-separated list of single event IDs.')
    parser.add_argument('-c', '--cover', type=str, help='Path to a local cover image file to use for ALL events.')
    parser.add_argument('-s', '--series', nargs=2, action='append', 
                        metavar=('SERIES_ID', 'PREFIX'), 
                        help='A series page ID and the event prefix to filter by. Can be used multiple times.')
    parser.add_argument('--preview', action='store_true', help='Preview API payload without creating events.')
    args = parser.parse_args()

    if not args.events and not args.series:
        parser.print_help()
        print("\nError: You must provide at least one event or series.")
        return

    cover_photo_id = None
    if args.cover and not args.preview:
        cover_photo_id = upload_photo_for_event(args.cover)
        if not cover_photo_id:
            print("Exiting due to cover photo upload failure.")
            return

    all_event_ids = []
    if args.series:
        for series_id, prefix in args.series:
            all_event_ids.extend(scrape_series_for_event_ids(series_id, prefix))
    if args.events:
        all_event_ids.extend([eid.strip() for eid in args.events.split(',')])

    unique_event_ids = list(dict.fromkeys(all_event_ids))
    if not unique_event_ids:
        print("\nNo event IDs to process.")
        return

    print(f"\nReady to process a total of {len(unique_event_ids)} unique events.")
    for event_id in unique_event_ids:
        print(f"\n{'='*50}\nProcessing Event ID: {event_id}\n{'='*50}")
        scraped_data = scrape_pasito_event(event_id)
        if not scraped_data:
            print(f"Skipping event ID {event_id} due to scraping error.")
            continue
        
        scraped_data["description"] = translate_description(scraped_data["description"])
        
        user_event_details = get_event_details_from_user(
            scraped_data["name"], 
            scraped_data["location_details"], 
            scraped_data["scraped_time"],
            scraped_data["scraped_date"]
        )

        final_payload = {
            "name": scraped_data["name"],
            "description": scraped_data["description"],
            "cover_url": scraped_data["cover_url"],
            **user_event_details
        }
        
        if args.preview:
            preview_facebook_payload(final_payload)
        else:
            create_facebook_event(final_payload, cover_photo_id)
    
    print(f"\n{'='*50}\nAll events processed.\n{'='*50}")

if __name__ == "__main__":
    main(), line)
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

def scrape_pasito_event(event_id):
    """Scrapes the main event page for all relevant details."""
    url = f"{BASE_PASITO_URL}/e/{event_id}"
    print(f"Scraping event page: {url}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
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
        
        description = ' '.join(desc_lines).strip()
        
        # If we found an event title in the page, use that instead of the HTML title
        if event_title_in_page:
            name = event_title_in_page
        
        # Extract cover image from meta tag
        cover_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            cover_url = og_image['content']
        
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
        
        # Extract location
        location_details = extract_location_from_text(soup)
        
        print("Event page scraping successful.")
        return {
            "name": name,
            "description": description,
            "cover_url": cover_url,
            "scraped_time": scraped_time,
            "scraped_date": scraped_date,
            "location_details": location_details
        }
    except requests.RequestException as e:
        print(f" Error: Could not fetch URL. {e}")
        return None

def translate_description(text):
    if not text: return ""
    try:
        translator = Translator()
        detected = translator.detect(text)
        if detected.lang != 'en':
            print("Translating description to English...")
            return translator.translate(text, dest='en').text
        return text
    except Exception as e:
        print(f"Warning: Could not translate text. Using original. Error: {e}")
        return text

def get_event_details_from_user(event_name, scraped_location_details, scraped_time, scraped_date):
    """Prompts only for details that couldn't be scraped."""
    print(f"\nPlease provide the details for the event: \"{event_name}\"")
    
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
            print("Could not parse time from page.")

    # Get date input
    if scraped_date:
        start_date_str = input(f"- Event Start Date (YYYY-MM-DD) [Found: {scraped_date}]: ")
        if not start_date_str.strip():
            # Try to convert scraped date to full date
            try:
                current_year = datetime.now().year
                parsed_date = datetime.strptime(f"{scraped_date} {current_year}", "%b %d %Y")
                start_date_str = parsed_date.strftime("%Y-%m-%d")
                print(f"Using converted date: {start_date_str}")
            except:
                start_date_str = input("- Event Start Date (YYYY-MM-DD): ")
    else:
        start_date_str = input("- Event Start Date (YYYY-MM-DD): ")
    
    if not start_time_obj:
        start_time_str = input("- Event Start Time (HH:MM, 24-hour format): ")
    if not duration_hours:
        duration_hours = float(input("- Event duration in hours (e.g., 2.5): "))
        
    timezone_str = input(f"- Timezone [America/Denver]: ") or "America/Denver"
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
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
        print("Could not automatically determine location, please provide details manually:")
        is_online = input("- Is the event online? (y/n): ").lower() == 'y'
        final_details["is_online"] = is_online
        if not is_online:
            final_details["place"] = {
                "name": input("  - Venue Name: "), 
                "location": {
                    "street": input("  - Street: "), 
                    "city": input("  - City: "), 
                    "state": input("  - State: "), 
                    "zip": input("  - Zip: "), 
                    "country": "US"
                }
            }

    return final_details

def create_facebook_event(event_data, cover_photo_id=None):
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("Error: Missing Facebook credentials. Cannot post event.")
        return
    if cover_photo_id:
        event_data["cover"] = {"source": cover_photo_id}
        if "cover_url" in event_data: del event_data["cover_url"]
        print("Using local cover image for event.")
    else:
        print("Using scraped cover image for event.")
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
    print("\n" + "="*60)
    print("FACEBOOK EVENT PAYLOAD PREVIEW")
    print("="*60)
    print(json.dumps(event_data, indent=2, default=str))
    print("="*60)

def main():
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("Error: Missing required environment variables FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN.")
        return

    parser = argparse.ArgumentParser(description="Create Facebook events by scraping Pasito.fun pages.")
    parser.add_argument('-e', '--events', type=str, help='Comma-separated list of single event IDs.')
    parser.add_argument('-c', '--cover', type=str, help='Path to a local cover image file to use for ALL events.')
    parser.add_argument('-s', '--series', nargs=2, action='append', 
                        metavar=('SERIES_ID', 'PREFIX'), 
                        help='A series page ID and the event prefix to filter by. Can be used multiple times.')
    parser.add_argument('--preview', action='store_true', help='Preview API payload without creating events.')
    args = parser.parse_args()

    if not args.events and not args.series:
        parser.print_help()
        print("\nError: You must provide at least one event or series.")
        return

    cover_photo_id = None
    if args.cover and not args.preview:
        cover_photo_id = upload_photo_for_event(args.cover)
        if not cover_photo_id:
            print("Exiting due to cover photo upload failure.")
            return

    all_event_ids = []
    if args.series:
        for series_id, prefix in args.series:
            all_event_ids.extend(scrape_series_for_event_ids(series_id, prefix))
    if args.events:
        all_event_ids.extend([eid.strip() for eid in args.events.split(',')])

    unique_event_ids = list(dict.fromkeys(all_event_ids))
    if not unique_event_ids:
        print("\nNo event IDs to process.")
        return

    print(f"\nReady to process a total of {len(unique_event_ids)} unique events.")
    for event_id in unique_event_ids:
        print(f"\n{'='*50}\nProcessing Event ID: {event_id}\n{'='*50}")
        scraped_data = scrape_pasito_event(event_id)
        if not scraped_data:
            print(f"Skipping event ID {event_id} due to scraping error.")
            continue
        
        scraped_data["description"] = translate_description(scraped_data["description"])
        
        user_event_details = get_event_details_from_user(
            scraped_data["name"], 
            scraped_data["location_details"], 
            scraped_data["scraped_time"],
            scraped_data["scraped_date"]
        )

        final_payload = {
            "name": scraped_data["name"],
            "description": scraped_data["description"],
            "cover_url": scraped_data["cover_url"],
            **user_event_details
        }
        
        if args.preview:
            preview_facebook_payload(final_payload)
        else:
            create_facebook_event(final_payload, cover_photo_id)
    
    print(f"\n{'='*50}\nAll events processed.\n{'='*50}")

if __name__ == "__main__":
    main()