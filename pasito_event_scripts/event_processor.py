"""Event processing functionality for Facebook event creation.

This module provides utilities for scraping, processing, and validating event data
before creating Facebook events.
"""

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class EventProcessingError(Exception):
    """Base exception for event processing errors."""


class ScrapingError(EventProcessingError):
    """Raised when event data scraping fails."""


class ValidationError(EventProcessingError):
    """Raised when event data validation fails."""


# Constants
REQUEST_TIMEOUT = 30  # seconds
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)


def scrape_pasito_event(url: str, logger: logging.Logger) -> Dict[str, Any]:
    """Scrape event details from a Pasito event page.

    Args:
        url: URL of the Pasito event page.
        logger: Logger instance for logging.

    Returns:
        Dictionary containing event details including:
        - title: Event title
        - description: Event description
        - start_time: Event start time
        - end_time: Event end time
        - location: Event location details
        - cover_image: URL of the event cover image
        - ticket_url: URL for ticket purchase

    Raises:
        ScrapingError: If scraping fails.
    """
    try:
        # Fetch the event page
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info("Successfully fetched event page")

        # Parse the HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract event details
        event_data = {
            "title": _extract_title(soup),
            "description": _extract_description(soup),
            "start_time": _extract_start_time(soup),
            "end_time": _extract_end_time(soup),
            "location": _extract_location(soup),
            "cover_image": _extract_cover_image(soup),
            "ticket_url": _extract_ticket_url(soup),
            "source_url": url,
        }

        logger.info("Successfully scraped event data")
        return event_data

    except requests.RequestException as e:
        logger.error(f"Failed to fetch event page: {str(e)}")
        raise ScrapingError(f"Failed to fetch event page: {str(e)}") from e
    except Exception as e:
        logger.error(f"Failed to scrape event data: {str(e)}")
        raise ScrapingError(f"Failed to scrape event data: {str(e)}") from e


def process_event_data(
    raw_data: Dict[str, Any], logger: logging.Logger
) -> Dict[str, Any]:
    """Process and validate event data before creating Facebook event.

    Args:
        raw_data: Raw event data from scraping.
        logger: Logger instance for logging.

    Returns:
        Processed event data ready for Facebook event creation.

    Raises:
        ValidationError: If required fields are missing or invalid.
    """
    try:
        # Validate required fields
        required_fields = ["title", "description", "start_time", "location"]
        for field in required_fields:
            if not raw_data.get(field):
                raise ValidationError(f"Missing required field: {field}")

        # Process and validate dates
        start_time = _validate_datetime(raw_data["start_time"])
        end_time = (
            _validate_datetime(raw_data["end_time"])
            if raw_data.get("end_time")
            else None
        )

        # Process location
        location = _process_location_data(raw_data["location"])

        # Process description
        description = format_event_description(
            raw_data["description"],
            raw_data.get("ticket_url"),
            raw_data["source_url"],
            logger,
        )

        processed_data = {
            "title": raw_data["title"].strip(),
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "cover_image": raw_data.get("cover_image"),
            "ticket_url": raw_data.get("ticket_url"),
        }

        logger.info("Successfully processed event data")
        return processed_data

    except Exception as e:
        logger.error("Failed to process event data: %s", str(e))
        raise ValidationError(f"Failed to process event data: {str(e)}") from e


def download_and_upload_image(
    image_url: str, driver: webdriver.Chrome, logger: logging.Logger
) -> str:
    """Download event image and upload it to Facebook.

    Args:
        image_url: URL of the event image.
        driver: Chrome WebDriver instance.
        logger: Logger instance for logging.

    Returns:
        Facebook image ID or URL.

    Raises:
        EventProcessingError: If image processing fails.
    """
    try:
        # Download image
        response = requests.get(image_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            suffix=".jpg",
            delete=False,
            dir=TEMP_DIR
        ) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        logger.info("Successfully downloaded image")

        # Upload to Facebook
        image_id = _upload_to_facebook(driver, temp_path, logger)

        # Clean up
        os.unlink(temp_path)

        return image_id

    except Exception as e:
        logger.error("Failed to process image: %s", str(e))
        raise EventProcessingError(f"Failed to process image: {str(e)}") from e


def process_location(
    location_data: Dict[str, Any], driver: webdriver.Chrome, logger: logging.Logger
) -> Dict[str, Any]:
    """Process location data and get Facebook location details.

    Args:
        location_data: Raw location data from event.
        driver: Chrome WebDriver instance.
        logger: Logger instance for logging.

    Returns:
        Processed location data for Facebook event.

    Raises:
        EventProcessingError: If location processing fails.
    """
    try:
        # Search for location on Facebook
        location_id = _search_facebook_location(driver, location_data["name"])

        if not location_id:
            # If location not found, create a new one
            location_id = _create_facebook_location(driver, location_data)

        return {
            "id": location_id,
            "name": location_data.get("name", ""),
            "address": location_data.get("address", ""),
            "city": location_data.get("city", ""),
            "country": location_data.get("country", ""),
        }

    except Exception as e:
        logger.error("Failed to process location: %s", str(e))
        raise EventProcessingError(f"Failed to process location: {str(e)}") from e


def format_event_description(
    description: str, ticket_url: Optional[str], source_url: str, logger: logging.Logger
) -> str:
    """Format event description with ticket link and source attribution.

    Args:
        description: Original event description.
        ticket_url: URL for ticket purchase.
        source_url: URL of the original event page.
        logger: Logger instance for logging.

    Returns:
        Formatted description ready for Facebook event.
    """
    del logger  # Unused.
    formatted_desc = description.strip()
    # Add ticket link if available
    if ticket_url:
        formatted_desc += f"\n\n🎟️ Get tickets: {ticket_url}"
    # Add source attribution
    formatted_desc += f"\n\nSource: {source_url}"
    return formatted_desc


def validate_event_creation(
    driver: webdriver.Chrome, event_data: Dict[str, Any], logger: logging.Logger
) -> bool:
    """Validate that the event was created successfully.

    Args:
        driver: Chrome WebDriver instance.
        event_data: Event data used for creation.
        logger: Logger instance for logging.

    Returns:
        True if event was created successfully, False otherwise.
    """
    try:
        # Check if event page exists
        event_url = driver.current_url
        if not event_url or "facebook.com/events" not in event_url:
            logger.error("Event page not found")
            return False

        # Verify event details
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
        )
        if title_element.text != event_data["title"]:
            logger.error("Event title mismatch")
            return False

        logger.info("Event creation validated successfully")
        return True

    except Exception as e:
        logger.error("Failed to validate event creation: %s", str(e))
        return False


def handle_creation_error(
    error: Exception, driver: webdriver.Chrome, logger: logging.Logger
) -> None:
    """Handle errors during event creation and attempt recovery.

    Args:
        error: The exception that occurred.
        driver: Chrome WebDriver instance.
        logger: Logger instance for logging.

    Raises:
        Exception: If recovery is not possible.
    """
    try:
        # Log the error
        logger.error("Event creation error: %s", str(error))

        # Take screenshot for debugging
        screenshot_path = (
            TEMP_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        driver.save_screenshot(str(screenshot_path))
        logger.info("Error screenshot saved to %s", screenshot_path)

        # Attempt to recover based on error type
        if "network" in str(error).lower():
            logger.info("Attempting to recover from network error")
            driver.refresh()
            return

        if "element not found" in str(error).lower():
            logger.info("Attempting to recover from element not found error")
            driver.refresh()
            return

        # If recovery not possible, raise the original error
        raise error

    except Exception as e:
        logger.error("Failed to handle error: %s", str(e))
        raise


# Helper functions
def _extract_title(soup: BeautifulSoup) -> str:
    """Extract event title from BeautifulSoup object."""
    title_elem = soup.find("h1")
    return title_elem.text.strip() if title_elem else ""


def _extract_description(soup: BeautifulSoup) -> str:
    """Extract event description from BeautifulSoup object."""
    desc_elem = soup.find("div", class_="event-description")
    return desc_elem.text.strip() if desc_elem else ""


def _extract_start_time(soup: BeautifulSoup) -> str:
    """Extract event start time from BeautifulSoup object."""
    time_elem = soup.find("time")
    return time_elem.get("datetime", "") if time_elem else ""


def _extract_end_time(soup: BeautifulSoup) -> str:
    """Extract event end time from BeautifulSoup object."""
    time_elem = soup.find("time", class_="end-time")
    return time_elem.get("datetime", "") if time_elem else ""


def _extract_location(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract event location from BeautifulSoup object."""
    location_elem = soup.find("div", class_="event-location")
    if not location_elem:
        return {}

    return {
        "name": (
            location_elem.find("h3").text.strip() if location_elem.find("h3") else ""
        ),
        "address": (
            location_elem.find("p").text.strip() if location_elem.find("p") else ""
        ),
        "city": (
            location_elem.find("span", class_="city").text.strip()
            if location_elem.find("span", class_="city")
            else ""
        ),
        "country": (
            location_elem.find("span", class_="country").text.strip()
            if location_elem.find("span", class_="country")
            else ""
        ),
    }


def _extract_cover_image(soup: BeautifulSoup) -> str:
    """Extract event cover image URL from BeautifulSoup object."""
    img_elem = soup.find("img", class_="event-cover")
    return img_elem.get("src", "") if img_elem else ""


def _extract_ticket_url(soup: BeautifulSoup) -> str:
    """Extract ticket purchase URL from BeautifulSoup object."""
    ticket_elem = soup.find("a", class_="ticket-link")
    return ticket_elem.get("href", "") if ticket_elem else ""


def _validate_datetime(dt_str: str) -> datetime:
    """Validate and parse datetime string."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValidationError(f"Invalid datetime format: {str(e)}") from e


def _process_location_data(location: Dict[str, str]) -> Dict[str, str]:
    """Process and validate location data."""
    required_fields = ["name", "address"]
    for field in required_fields:
        if not location.get(field):
            raise ValidationError(f"Missing required location field: {field}")

    return {
        "name": location["name"].strip(),
        "address": location["address"].strip(),
        "city": location.get("city", "").strip(),
        "country": location.get("country", "").strip(),
    }


def _upload_to_facebook(
    driver: webdriver.Chrome, image_path: str, logger: logging.Logger
) -> str:
    """Upload image to Facebook and return image ID."""
    # Note: This is a placeholder implementation
    # The actual implementation would depend on Facebook's image upload interface
    logger.info("Uploading image to Facebook: %s", image_path)
    return "placeholder_image_id"


def _search_facebook_location(
    driver: webdriver.Chrome, location_name: str
) -> Optional[Dict[str, str]]:
    """Search for location on Facebook and return location ID if found."""
    # Note: This is a placeholder implementation
    # The actual implementation would depend on Facebook's location search interface
    # logger is not used here, so we do not reference it
    return None


def _create_facebook_location(
    driver: webdriver.Chrome, location_data: Dict[str, Any]
) -> str:
    """Create new location on Facebook and return location ID."""
    # Note: This is a placeholder implementation
    # The actual implementation would depend on Facebook's location creation interface
    # logger is not used here, so we do not reference it
    return "placeholder_location_id"
