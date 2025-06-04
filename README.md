# Facebook Event Creator for Pasito.fun

This script automates the process of creating Facebook events from Pasito.fun event listings. It can scrape individual events or entire series, translate descriptions if needed, and create corresponding Facebook events with proper timezone handling.

## Features

- Web scraping of Pasito.fun event pages and series
- Automatic translation of event descriptions to English
- Timezone-aware event scheduling
- Support for both online and physical events
- Automatic location detection from event pages
- Custom cover image support
- Command-line interface for batch processing
- Facebook Graph API integration

## Prerequisites

- Python 3.7 or higher
- Facebook Page access token with `pages_manage_events` permission
- Facebook Page ID

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Facebook credentials:
```
FB_PAGE_ID=your_page_id_here
FB_PAGE_ACCESS_TOKEN=your_access_token_here
```

## Usage

The script can be used in several ways:

### 1. Process Individual Events

```bash
python create_fb_event.py -e "event_id1,event_id2,event_id3"
```

### 2. Process Events from a Series

```bash
python create_fb_event.py -s "series_id" "event_prefix"
```

You can process multiple series:
```bash
python create_fb_event.py -s "series1_id" "prefix1" -s "series2_id" "prefix2"
```

### 3. Use a Custom Cover Image

```bash
python create_fb_event.py -e "event_id" -c "path/to/cover/image.jpg"
```

### 4. Combine Options

```bash
python create_fb_event.py -e "event_id1,event_id2" -s "series_id" "prefix" -c "cover.jpg"
```

## Command Line Arguments

- `-e, --events`: Comma-separated list of event IDs to process
- `-s, --series`: Process events from a series page (requires series ID and event prefix)
- `-c, --cover`: Path to a local cover image file to use for all events

## Environment Variables

- `FB_PAGE_ID`: Your Facebook Page ID
- `FB_PAGE_ACCESS_TOKEN`: Your Facebook Page access token with `pages_manage_events` permission

## Dependencies

- requests: For making HTTP requests
- beautifulsoup4: For web scraping
- googletrans: For text translation
- pytz: For timezone handling
- python-dotenv: For environment variable management

## Error Handling

The script includes comprehensive error handling for:
- Network issues
- Invalid URLs
- Missing or invalid Facebook credentials
- Translation failures
- Invalid timezone inputs
- Facebook API errors
- Cover image upload failures
- Series scraping errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 