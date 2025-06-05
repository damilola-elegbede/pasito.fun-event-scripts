# Pasito Event Scripts

A Python package for automating event management tasks for Pasito events, particularly focusing on Facebook event creation from Pasito event pages.

## Features

- Automated Facebook event creation from Pasito event pages
- Robust error handling and logging
- Type hints for better code maintainability
- Comprehensive test coverage
- Modern Python packaging and development tools

## Installation

1. Clone the repository:
```bash
git clone https://github.com/damilola-elegbede/pasito.fun-event-scripts.git
cd pasito.fun-event-scripts
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in development mode:
```bash
pip install -e .
```

## Configuration

1. Create a `.env` file in the project root with the following variables:
```env
FB_EMAIL
FB_PASSWORD
FB_GROUP_ID
```

2. Make sure you have Chrome browser installed for Selenium WebDriver.

## Usage

### Command Line Interface

The main script can be run using:
```bash
create-fb-event <event_url>
```

Example:
```bash
create-fb-event https://pasito.fun/events/example-event
```

### Python API

You can also use the package programmatically:

```python
from pasito_event_scripts.create_fb_event import main

# Create a Facebook event from a Pasito event URL
main(["https://pasito.fun/events/example-event"])
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=pasito_event_scripts

# Run specific test file
pytest tests/test_create_fb_event.py
```

### Code Quality

The project uses several tools to maintain code quality:

```bash
# Format code with Black
black .

# Check code style with Flake8
flake8

# Type checking with MyPy
mypy .
```

### Project Structure

```
pasito.fun-event-scripts/
├── docs/                  # Documentation
├── logs/                  # Log files
├── pasito_event_scripts/  # Package source code
│   ├── __init__.py
│   └── create_fb_event.py
├── tests/                 # Test files
├── temp/                  # Temporary files
├── .env                   # Environment variables
├── .gitignore            # Git ignore patterns
├── README.md             # Project documentation
├── requirements.txt      # Project dependencies
├── setup.py              # Package setup
├── setup.cfg             # Linting configuration
└── pyproject.toml        # Black configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Selenium](https://www.selenium.dev/) for web automation
- [Python-dotenv](https://github.com/theskumar/python-dotenv) for environment variable management
- [WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager) for ChromeDriver management 