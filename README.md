# Pasito to Facebook Event Creator

This script automatically creates Facebook events from Pasito event pages. It can process individual events or entire series of events, making it easy to sync your dance events across platforms.

## Features

- 🎯 Process single events or entire series
- 🌐 Automatically scrapes event details from Pasito
- 📍 Handles location details and venue information
- 🌍 Translates non-English descriptions to English
- 🔗 Adds source link to the event description
- 👀 Preview mode for testing without creating events
- 🕒 Handles timezone conversion automatically

## Prerequisites

- Python 3.7 or higher
- A Facebook Page with admin access
- Facebook Page Access Token with required permissions
- Chrome browser (for Selenium)

## Dependencies

The script requires the following Python packages:
- `requests>=2.31.0`: For making HTTP requests
- `beautifulsoup4>=4.12.2`: For HTML parsing
- `deep-translator>=1.11.4`: For text translation
- `pytz>=2024.1`: For timezone handling
- `python-dotenv>=1.0.0`: For environment variable management
- `selenium>=4.18.1`: For web scraping
- `webdriver-manager>=4.0.1`: For managing Chrome WebDriver

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pasito.fun-event-scripts.git
   cd pasito.fun-event-scripts
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   # Set these in your shell or create a .env file
   export FB_PAGE_ID="your_page_id"
   export FB_PAGE_ACCESS_TOKEN="your_access_token"
   ```

## Facebook Setup

1. Create a Facebook Page if you haven't already
2. Get your Page ID from the About section of your Facebook Page
3. Generate a Page Access Token with the following permissions:
   - `pages_manage_events`
   - `pages_read_engagement`

## Usage

### Process a Single Event

```bash
python create_fb_event.py <event_id> [--preview]

# Example:
python create_fb_event.py blue-ice-bachata-night-r14by --preview
```

### Process Events from a Series

```bash
python create_fb_event.py --series <series_id> [--prefix <prefix>] [--preview]

# Example:
python create_fb_event.py --series boulder-salsa-bachata-rueda-wc-swing-social-xd9r4 --preview
```

### Command-line Options

- `--preview`: Preview the Facebook API payload without creating the event
- `--series`: Process all events from a series
- `--prefix`: Filter series events by prefix (optional)

## How It Works

1. The script scrapes event details from Pasito using Selenium
2. Extracts key information:
   - Event name and description
   - Date and time
   - Location details
   - Venue information
3. Translates non-English content to English
4. Adds a source link to the event description
5. Creates the event on Facebook using the Graph API

## Output

The script provides detailed output about:
- Scraping progress
- Location detection
- Event creation status
- Any errors or warnings

In preview mode, it saves the Facebook API payload to `facebook_api_preview.txt` for review.

## Error Handling

The script includes comprehensive error handling for:
- Network issues
- Invalid URLs
- Missing or invalid Facebook credentials
- Translation failures
- Invalid timezone inputs
- Facebook API errors
- Series scraping errors

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 