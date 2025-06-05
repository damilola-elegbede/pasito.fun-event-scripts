# Pasito Event Scripts

This repository contains scripts for automating event management tasks for Pasito events.

## Facebook Event Creator

The `create_fb_event.py` script automatically creates Facebook events from Pasito event pages. It can process individual events or entire series of events.

### Features

- 🎯 Process single events or entire series
- 🔍 Automatically scrapes event details from Pasito
- 📍 Handles location details and venue information
- 🌐 Translates non-English descriptions to English
- 🔗 Adds source link to the event description
- 👀 Preview mode for testing without creating events
- 🧹 Cleanup option for temporary files
- 🔄 Supports both event IDs and full URLs

### Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- Facebook Page with admin access
- Facebook Page Access Token with required permissions

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/damilola-elegbede/pasito.fun-event-scripts.git
   cd pasito.fun-event-scripts
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   export FB_PAGE_ID="your_page_id"
   export FB_PAGE_ACCESS_TOKEN="your_access_token"
   ```
   Or create a `.env` file with these variables.

### Facebook Setup

1. Create a Facebook Page if you don't have one
2. Generate a Page Access Token with these permissions:
   - `pages_manage_events`
   - `pages_read_engagement`

### Usage

The script requires either `-e/--events` or `-s/--series` flag to be present.

#### Process Single Events

You can provide event IDs or full URLs:

```bash
# Using event IDs
python create_fb_event.py -e event-id-1 event-id-2

# Using full URLs
python create_fb_event.py -e https://pasito.fun/e/event-id-1 https://pasito.fun/e/event-id-2

# Mix of IDs and URLs
python create_fb_event.py -e event-id-1 https://pasito.fun/e/event-id-2
```

#### Process Series

You can provide a series ID or full URL:

```bash
# Using series ID
python create_fb_event.py -s series-id

# Using full URL
python create_fb_event.py -s https://pasito.fun/es/series-id
```

#### Command-line Options

Required:
- `-e, --events`: One or more event IDs or full URLs (e.g., `https://pasito.fun/e/event-id`)
- `-s, --series`: Series ID or full URL to scrape for event IDs

Optional:
- `-p, --preview`: Preview API payload without creating events
- `-c, --clean`: Clean up temporary files after preview
- `--page-id`: Facebook Page ID (overrides FB_PAGE_ID environment variable)
- `--access-token`: Facebook Page Access Token (overrides FB_PAGE_ACCESS_TOKEN environment variable)

### How It Works

1. **Event Scraping**:
   - For single events: Scrapes the event page directly
   - For series: Scrapes the series page to find all event links

2. **Data Processing**:
   - Extracts event details (name, description, date, time)
   - Handles location information
   - Translates non-English descriptions
   - Adds source link to description

3. **Facebook Integration**:
   - Creates events using Facebook Graph API
   - Handles timezone conversion
   - Manages location details

### Output

The script generates two temporary files in preview mode:
- `raw.txt`: Contains the raw HTML from the scraped event page
- `facebook_api_preview.txt`: Contains the preview of the Facebook API payload

These files are automatically cleaned up when using the `--clean` flag.

### Error Handling

The script includes comprehensive error handling for:
- Invalid event IDs or URLs
- Missing Facebook credentials
- Network issues
- Invalid date/time formats
- Missing location information

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 