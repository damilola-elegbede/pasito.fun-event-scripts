import requests
import os
import json
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from googletrans import Translator
from datetime import datetime, timedelta
import pytz

# --- CONFIGURATION ---
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
GRAPH_API_VERSION = "v20.0"
BASE_PASITO_URL = "https://pasito.fun"

def upload_photo_for_event(image_path):
    """
    Uploads a local photo to the Page's photos without publishing it to the feed.
    Returns the photo ID needed for the event cover.
    """
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
    except Exception as e:
        print(f" An unexpected error occurred during photo upload: {e}")
        return None

def scrape_series_for_event_ids(series_id, prefix):
    """
    Scrapes a Pasito.fun series page and filters for events with a specific prefix.
    """
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

def scrape_pasito_event(event_id):
    """
    Scrapes the details from a given pasito.fun event ID, now including location.
    """
    url = f"{BASE_PASITO_URL}/e/{event_id}"
    print(f"Scraping event details from {url}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        name = soup.find('h1').get_text(strip=True)
        about_header = soup.find('h2', string='About')
        description = about_header.find_next_sibling('p').get_text(strip=True) if about_header else ""
        cover_url = soup.find('meta', property='og:image')['content']
        
        # *** NEW: Scrape location information ***
        location = None
        location_tag = soup.find('a', href=lambda href: href and "maps.google.com" in href)
        if location_tag:
            location_text = location_tag.get_text(separator='\n', strip=True).split('\n')
            if len(location_text) >= 2:
                venue_name = location_text[0]
                address_parts = location_text[1].split(',')
                street = address_parts[0].strip()
                city_state_zip = address_parts[1].strip().split()
                city = " ".join(city_state_zip[:-2])
                state = city_state_zip[-2]
                zip_code = city_state_zip[-1]
                
                location = {
                    "is_online": False,
                    "place": {
                        "name": venue_name,
                        "location": {"street": street, "city": city, "state": state, "zip": zip_code, "country": "US"}
                    }
                }
                print(f"Found location on page: {venue_name}")

        print("Scraping successful.")
        return {"name": name, "description": description, "cover_url": cover_url, "location": location}

    except requests.RequestException as e:
        print(f" Error: Could not fetch URL. {e}")
        return None
    except (AttributeError, TypeError) as e:
        print(f" Error: Could not parse the webpage for ID {event_id}. Its structure might have changed. {e}")
        return None

def translate_description(text):
    """Translates the description text to English."""
    if not text: return ""
    try:
        translator = Translator()
        if translator.detect(text).lang != 'en':
            print("Translating description to English...")
            return translator.translate(text, dest='en').text
        return text
    except Exception as e:
        print(f"Warning: Could not translate text. Using original. Error: {e}")
        return text

def get_event_details_from_user(event_name, scraped_location=None):
    """
    Prompts the user for event details, skipping location if already scraped.
    """
    print(f"\nPlease provide the details for the event: \"{event_name}\"")
    start_date_str = input("- Event Start Date (YYYY-MM-DD): ")
    start_time_str = input("- Event Start Time (HH:MM, 24-hour format): ")
    duration_hours = float(input("- Event duration in hours (e.g., 2.5): "))
    timezone_str = input(f"- Timezone [Boulder, Colorado]: ") or "America/Denver"
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        print(f"Invalid timezone '{timezone_str}'. Defaulting to 'America/Denver'.")
        tz = pytz.timezone("America/Denver")
    start_datetime_local = tz.localize(datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M"))
    end_datetime_local = start_datetime_local + timedelta(hours=duration_hours)
    start_time_utc = start_datetime_local.astimezone(pytz.utc).isoformat()
    end_time_utc = end_datetime_local.astimezone(pytz.utc).isoformat()
    
    # *** NEW: Check if location was scraped before asking the user ***
    if scraped_location:
        return {"start_time": start_time_utc, "end_time": end_time_utc, "event_time_zone": timezone_str, **scraped_location}

    # Fallback to asking user if location wasn't on the page
    print("No location found on page, please provide details manually:")
    is_online = input("- Is the event online? (y/n): ").lower() == 'y'
    event_location = {}
    if not is_online:
        print("  Please provide the physical location:")
        event_location = {"name": input("  - Venue Name: "), "location": {"street": input("  - Street: "), "city": input("  - City: "), "state": input("  - State: "), "zip": input("  - Zip: "), "country": "US"}}
    return {"start_time": start_time_utc, "end_time": end_time_utc, "event_time_zone": timezone_str, "is_online": is_online, "place": event_location}


def create_facebook_event(event_data, cover_photo_id=None):
    """Posts the final event data to the Facebook Graph API."""
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
    except requests.RequestException as e:
        print(f"\n❌ Error: Failed to create Facebook event. Status Code: {e.response.status_code}, Response: {e.response.text}")

def main():
    """Main function to parse arguments and run the script."""
    if not FB_PAGE_ID or not FB_PAGE_ACCESS_TOKEN:
        print("Error: Missing required environment variables FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN.")
        return

    parser = argparse.ArgumentParser(description="Create Facebook events by scraping Pasito.fun pages.")
    parser.add_argument('-e', '--events', type=str, help='Comma-separated list of single event IDs.')
    parser.add_argument('-c', '--cover', type=str, help='Path to a local cover image file to use for ALL events.')
    parser.add_argument('-s', '--series', nargs=2, action='append', 
                        metavar=('SERIES_ID', 'PREFIX'), 
                        help='A series page ID and the event prefix to filter by. Can be used multiple times.')

    args = parser.parse_args()

    if not args.events and not args.series:
        parser.print_help()
        print("\nError: You must provide at least one event or series.")
        return

    cover_photo_id = None
    if args.cover:
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
        
        # Pass the scraped location (or None) to the user input function
        user_event_details = get_event_details_from_user(scraped_data["name"], scraped_data["location"])

        final_payload = {
            "name": scraped_data["name"],
            "description": scraped_data["description"],
            "cover_url": scraped_data["cover_url"],
            "start_time": user_event_details["start_time"],
            "end_time": user_event_details["end_time"],
            "event_time_zone": user_event_details["event_time_zone"]
        }
        if "is_online" in user_event_details and user_event_details["is_online"]:
            final_payload["is_online"] = True
        elif "place" in user_event_details:
            final_payload["place"] = user_event_details["place"]
        
        create_facebook_event(final_payload, cover_photo_id)
    
    print(f"\n{'='*50}\nAll events processed.\n{'='*50}")

if __name__ == "__main__":
    main()