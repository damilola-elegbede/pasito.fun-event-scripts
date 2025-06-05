# Pasito Event Scripts Documentation

## Overview
This project contains scripts for automating event management tasks for Pasito events, particularly focusing on Facebook event creation from Pasito event pages.

## Installation
```bash
pip install -e .
```

## Usage
The main script can be run using:
```bash
python -m pasito_event_scripts.create_fb_event <event_url>
```

## Development
1. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

3. Run tests:
```bash
pytest --maxfail=3 --disable-warnings -v
```

4. Run linting:
```bash
pylint pasito_event_scripts/ tests/
```

## Project Structure
- `pasito_event_scripts/`: Main package directory
  - `create_fb_event.py`: Main script for creating Facebook events
  - `event_processor.py`: Event data processing module
  - `__init__.py`: Package initialization
- `tests/`: Test files
- `docs/`: Documentation
- `.github/`: GitHub Actions workflows
  - `pre-commit.yml`: Pre-commit checks
  - `test.yml`: Test workflow
  - `post-commit.yml`: Post-commit checks

## Environment Variables
The following environment variables are required:
- `FB_EMAIL`: Facebook login email
- `FB_PASSWORD`: Facebook login password

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License
MIT License 