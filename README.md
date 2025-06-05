# Pasito.fun Event Scraper

A robust web scraper for extracting dance event data from [Pasito.fun](https://pasito.fun) and formatting it for Facebook API event creation.

## 🎯 Features

- **Event Data Extraction**: Scrapes comprehensive event details (name, times, venue, description)
- **Facebook API Ready**: Outputs clean JSON formatted for Facebook Graph API
- **Series Support**: Handles both individual events and event series
- **Browser Optimization**: Efficient Selenium session management with performance optimizations
- **Time Parsing**: Robust ISO 8601 time formatting with timezone support
- **Comprehensive Testing**: Full test suite with real HTML validation
- **CI/CD Ready**: GitHub Actions workflows and pre-commit hooks

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Chrome browser (for Selenium WebDriver)

### Installation

```bash
# Clone the repository
git clone https://github.com/damilola-elegbede/pasito.fun-event-scripts.git
cd pasito.fun-event-scripts

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Usage

#### Scrape Individual Event
```bash
python pasito_event_scraper.py -e "https://pasito.fun/event/your-event-url"
```

#### Scrape Event Series
```bash
python pasito_event_scraper.py -s "boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
```

### Example Output
```json
{
  "name": "Boulder Salsa, Bachata, Rueda, & WC Swing Social",
  "start_time": "2024-06-05T18:30:00-06:00",
  "end_time": "2024-06-05T23:00:00-06:00",
  "place": "The Avalon Ballroom",
  "description": "Join us for an evening of dancing! Salsa, Bachata, Rueda de Casino..."
}
```

## 🧪 Testing Framework

### Test Suite Overview

The project includes a comprehensive test suite with **13 tests** covering:

- **Utility Functions** (7 tests): Series ID extraction, time parsing, error handling
- **HTML Parsing** (6 tests): Real HTML structure validation, venue extraction, event details

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test class
pytest test_pasito_event_scraper.py::TestPasitoEventScraper -v
```

### Test Coverage

- ✅ **100% pass rate** in CI/CD
- ✅ **Real HTML validation** using actual Pasito event page structure
- ✅ **Error handling** for malformed data
- ✅ **Edge cases** for time parsing and URL extraction

## 🛡️ Pre-Commit Hooks

The repository includes **automated quality control** with pre-commit hooks that prevent commits when tests fail.

### How It Works

1. **Automatic Trigger**: Runs before every `git commit`
2. **Test Execution**: Executes full test suite (`pytest -v`)
3. **Commit Prevention**: Blocks commit if any tests fail
4. **Success Flow**: Allows commit only when all tests pass

### Example Behavior

**When tests fail:**
```bash
Running pre-commit tests...
Running pytest...
❌ Tests failed! Commit aborted.
Please fix failing tests before committing.
```

**When tests pass:**
```bash
Running pre-commit tests...
Running pytest...
✅ All tests passed! Proceeding with commit.
```

### Manual Test Running

You can run tests manually before committing:
```bash
pytest -v
```

## 🏗️ Architecture

### Core Components

- **`BrowserSession`**: Reusable Selenium WebDriver management
- **`extract_event_data()`**: Unified event parsing logic
- **`parse_time_to_iso8601()`**: Robust time formatting
- **`extract_series_id()`**: URL/ID normalization utilities

### Performance Optimizations

- **Single browser session** for multiple events (vs. new instance per event)
- **Disabled images/CSS** for faster page loading
- **Streamlined data pipeline** eliminating code duplication
- **Resource cleanup** with proper browser session management

## 📊 CI/CD Pipeline

### GitHub Actions Workflows

- **Pre-commit**: Runs on every push and pull request
- **Post-commit**: Validation and additional checks
- **Automated testing** with Python 3.13+ on Ubuntu

### Workflow Features

- ✅ **Dependency installation** including `lxml` parser
- ✅ **Full test suite execution**
- ✅ **Cross-platform compatibility**
- ✅ **Automated quality gates**

## 📁 Project Structure

```
pasito.fun-event-scripts/
├── pasito_event_scraper.py     # Main scraper script
├── test_pasito_event_scraper.py # Comprehensive test suite
├── requirements.txt            # Python dependencies
├── .gitignore                 # Git ignore patterns
├── .git/hooks/
│   ├── pre-commit             # Test validation hook
│   └── post-commit            # Post-commit processing
└── .github/workflows/
    ├── pre-commit.yml         # CI pre-commit workflow
    └── post-commit.yml        # CI post-commit workflow
```

## 🔧 Dependencies

- **`requests`**: HTTP client for web requests
- **`beautifulsoup4`**: HTML parsing and extraction
- **`selenium`**: Browser automation for JavaScript rendering
- **`lxml`**: Fast XML/HTML parser for BeautifulSoup
- **`pytz`**: Timezone handling for accurate time conversion
- **`pytest`**: Testing framework for quality assurance

## 🚀 Development Workflow

1. **Make changes** to code
2. **Run tests** locally: `pytest -v`
3. **Commit changes**: Pre-commit hook automatically validates
4. **Push to remote**: GitHub Actions runs CI/CD pipeline
5. **All quality gates** must pass for successful deployment

## 📈 Recent Improvements

- **Major refactoring**: Eliminated 300+ lines of duplicate code
- **Performance boost**: Single browser session for multiple events
- **Test coverage**: Added comprehensive test suite with real HTML validation
- **CI/CD integration**: GitHub Actions workflows with automated testing
- **Quality control**: Pre-commit hooks preventing broken code commits

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and ensure tests pass: `pytest -v`
4. Commit changes (pre-commit hook will validate)
5. Push to branch and create pull request

## 📄 License

This project is available for use under standard open source practices.
