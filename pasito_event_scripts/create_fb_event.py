"""Script for creating Facebook events from Pasito event pages.

This module provides functionality to automate the creation of Facebook events
from Pasito event pages using Selenium WebDriver.
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from .event_processor import (
    scrape_pasito_event,
    process_event_data,
    download_and_upload_image,
    validate_event_creation,
    handle_creation_error,
    EventProcessingError
)

# Load environment variables
load_dotenv()

# Constants
FB_EMAIL = os.getenv("FB_EMAIL")
FB_PASSWORD = os.getenv("FB_PASSWORD")
FB_GROUP_ID = os.getenv("FB_GROUP_ID")
LOG_DIR = Path("logs")
TEMP_DIR = Path("temp")

def setup_logging() -> logging.Logger:
    """Set up logging configuration.

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(exist_ok=True)

    # Set up logging
    logger = logging.getLogger("create_fb_event")
    logger.setLevel(logging.INFO)

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(
        LOG_DIR / f"create_fb_event_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    # Create formatters and add it to handlers
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def setup_driver() -> webdriver.Chrome:
    """Set up and configure Chrome WebDriver.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance.
    """
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def login_to_facebook(driver: webdriver.Chrome, logger: logging.Logger) -> None:
    """Log in to Facebook using credentials from environment variables.

    Args:
        driver: Chrome WebDriver instance.
        logger: Logger instance for logging.

    Raises:
        SystemExit: If credentials are missing or login fails.
    """
    if not all([FB_EMAIL, FB_PASSWORD]):
        logger.error("Facebook credentials not found in environment variables")
        sys.exit(1)

    try:
        driver.get("https://www.facebook.com")
        logger.info("Navigated to Facebook login page")

        # Wait for and fill in email
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_field.send_keys(FB_EMAIL)
        logger.info("Entered email")

        # Fill in password
        password_field = driver.find_element(By.ID, "pass")
        password_field.send_keys(FB_PASSWORD)
        logger.info("Entered password")

        # Click login button
        login_button = driver.find_element(By.NAME, "login")
        login_button.click()
        logger.info("Clicked login button")

        # Wait for login to complete
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Facebook']"))
        )
        logger.info("Successfully logged in to Facebook")

    except Exception as e:
        logger.error("Failed to log in to Facebook: %s", str(e))
        sys.exit(1)

def create_facebook_event(
    driver: webdriver.Chrome,
    event_data: Dict[str, Any],
    logger: logging.Logger
) -> None:
    """Create a Facebook event using the provided event data.

    Args:
        driver: Chrome WebDriver instance.
        event_data: Dictionary containing event details.
        logger: Logger instance for logging.

    Raises:
        EventProcessingError: If event creation fails.
    """
    try:
        # Navigate to group page
        driver.get(f"https://www.facebook.com/groups/{FB_GROUP_ID}")
        logger.info("Navigated to group page: %s", FB_GROUP_ID)

        # Click "Create Event" button
        create_event_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Create Event']"))
        )
        create_event_button.click()
        logger.info("Clicked Create Event button")

        # Fill in event details
        _fill_event_details(driver, event_data, logger)

        # Validate event creation
        if not validate_event_creation(driver, event_data, logger):
            raise EventProcessingError("Event creation validation failed")

        logger.info("Successfully created Facebook event")

    except Exception as e:
        handle_creation_error(e, driver, logger)
        raise

def _fill_event_details(
    driver: webdriver.Chrome,
    event_data: Dict[str, Any],
    logger: logging.Logger
) -> None:
    """Fill in event details in the Facebook event creation form.

    Args:
        driver: Chrome WebDriver instance.
        event_data: Dictionary containing event details.
        logger: Logger instance for logging.

    Raises:
        EventProcessingError: If filling event details fails.
    """
    try:
        # Fill in title
        title_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "event_name"))
        )
        title_field.send_keys(event_data["title"])
        logger.info("Entered event title")

        # Fill in description
        description_field = driver.find_element(By.NAME, "event_description")
        description_field.send_keys(event_data["description"])
        logger.info("Entered event description")

        # Fill in start time
        start_time_field = driver.find_element(By.NAME, "event_start_time")
        start_time_field.send_keys(event_data["start_time"].strftime("%Y-%m-%d %H:%M"))
        logger.info("Entered start time")

        # Fill in end time if available
        if event_data.get("end_time"):
            end_time_field = driver.find_element(By.NAME, "event_end_time")
            end_time_field.send_keys(event_data["end_time"].strftime("%Y-%m-%d %H:%M"))
            logger.info("Entered end time")

        # Fill in location
        location_field = driver.find_element(By.NAME, "event_location")
        location_field.send_keys(event_data["location"]["name"])
        logger.info("Entered location")

        # Upload cover image if available
        if event_data.get("cover_image"):
            image_id = download_and_upload_image(
                event_data["cover_image"],
                driver,
                logger
            )
            _upload_cover_image(driver, image_id, logger)

        # Click create button
        create_button = driver.find_element(By.XPATH, "//button[text()='Create']")
        create_button.click()
        logger.info("Clicked create button")

    except Exception as e:
        logger.error("Failed to fill event details: %s", str(e))
        raise EventProcessingError(f"Failed to fill event details: {str(e)}") from e

def _upload_cover_image(
    driver: webdriver.Chrome,
    image_id: str,
    logger: logging.Logger
) -> None:
    """Upload cover image to the event.

    Args:
        driver: Chrome WebDriver instance.
        image_id: Facebook image ID.
        logger: Logger instance for logging.

    Raises:
        EventProcessingError: If image upload fails.
    """
    try:
        # Click upload image button
        upload_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Upload')]")
        upload_button.click()

        # Select image
        image_input = driver.find_element(By.NAME, "composer_photo")
        image_input.send_keys(image_id)

        logger.info("Uploaded cover image")

    except Exception as e:
        logger.error("Failed to upload cover image: %s", str(e))
        raise EventProcessingError(f"Failed to upload cover image: {str(e)}") from e

def main(args: Optional[List[str]] = None) -> None:
    """Main function to create Facebook events from Pasito event pages.

    Args:
        args: Optional command line arguments.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Create Facebook events from Pasito event pages"
    )
    parser.add_argument(
        "event_url",
        help="URL of the Pasito event page"
    )
    parsed_args = parser.parse_args(args)

    # Set up logging
    logger = setup_logging()
    logger.info("Starting Facebook event creation process")

    try:
        # Set up WebDriver
        driver = setup_driver()
        logger.info("WebDriver setup completed")

        # Log in to Facebook
        login_to_facebook(driver, logger)

        # Scrape event data
        raw_event_data = scrape_pasito_event(parsed_args.event_url, logger)

        # Process event data
        event_data = process_event_data(raw_event_data, logger)

        # Create event
        create_facebook_event(driver, event_data, logger)

    except Exception as e:
        logger.error("An error occurred: %s", str(e))
        sys.exit(1)
    finally:
        if "driver" in locals():
            driver.quit()
            logger.info("WebDriver closed")

if __name__ == "__main__":
    main()
