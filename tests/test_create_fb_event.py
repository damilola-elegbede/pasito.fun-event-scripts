"""Tests for the create_fb_event module."""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from pasito_event_scripts.create_fb_event import (
    setup_logging,
    setup_driver,
    login_to_facebook,
    create_facebook_event,
    main
)

# Test data
TEST_EVENT_DATA = {
    "title": "Test Event",
    "description": "Test Description",
    "start_time": datetime(2024, 3, 20, 10, 0),
    "end_time": datetime(2024, 3, 20, 12, 0),
    "location": {
        "name": "Test Location",
        "address": "123 Main St",
        "city": "Test City",
        "country": "Test Country"
    },
    "cover_image": "https://example.com/image.jpg",
    "ticket_url": "https://tickets.com/event",
    "source_url": "https://example.com/event"
}

def test_setup_logging():
    """Test logging setup."""
    logger = setup_logging()
    assert logger.name == "create_fb_event"
    assert logger.level == 20  # INFO level

def test_setup_driver():
    """Test WebDriver setup."""
    with patch("pasito_event_scripts.create_fb_event.webdriver.Chrome") as mock_chrome:
        driver = setup_driver()
        assert mock_chrome.called

@patch.dict(os.environ, {
    "FB_EMAIL": "test@example.com",
    "FB_PASSWORD": "test_password"
})
def test_login_to_facebook_success():
    """Test successful Facebook login."""
    mock_driver = MagicMock()
    mock_logger = MagicMock()
    mock_wait = MagicMock()
    mock_element = MagicMock()
    mock_wait.until.return_value = mock_element
    with patch("pasito_event_scripts.create_fb_event.WebDriverWait", return_value=mock_wait), \
         patch("pasito_event_scripts.create_fb_event.FB_EMAIL", "test@example.com"), \
         patch("pasito_event_scripts.create_fb_event.FB_PASSWORD", "test_password"):
        login_to_facebook(mock_driver, mock_logger)
        mock_driver.get.assert_called_once_with("https://www.facebook.com")
        mock_element.send_keys.assert_called()
        mock_logger.info.assert_called()

@patch.dict(os.environ, {}, clear=True)
def test_login_to_facebook_missing_credentials():
    """Test Facebook login with missing credentials."""
    mock_driver = MagicMock()
    mock_logger = MagicMock()
    with pytest.raises(SystemExit) as excinfo:
        login_to_facebook(mock_driver, mock_logger)
    assert excinfo.value.code == 1
    mock_logger.error.assert_called_once()

@patch.dict(os.environ, {"FB_GROUP_ID": "123456789"})
def test_create_facebook_event_success():
    """Test successful Facebook event creation."""
    mock_driver = MagicMock()
    mock_logger = MagicMock()
    mock_wait = MagicMock()
    mock_element = MagicMock()
    mock_wait.until.return_value = mock_element
    fake_image_content = b"fake image data"
    mock_image_response = MagicMock()
    mock_image_response.status_code = 200
    mock_image_response.content = fake_image_content
    mock_image_response.raise_for_status.return_value = None
    with patch("pasito_event_scripts.create_fb_event.WebDriverWait", return_value=mock_wait), \
         patch("requests.get", return_value=mock_image_response), \
         patch("pasito_event_scripts.create_fb_event.validate_event_creation", return_value=True):
        create_facebook_event(mock_driver, TEST_EVENT_DATA, mock_logger)
        mock_driver.get.assert_called_once()
        mock_element.send_keys.assert_called()
        mock_logger.info.assert_called()

def test_main_function_success():
    """Test the main function with successful execution."""
    test_url = "https://example.com/event"
    fake_html = """
    <html><body>
    <h1>Test Event</h1>
    <div class='event-description'>Test Description</div>
    <time datetime='2024-03-20T10:00:00+00:00'></time>
    <time class='end-time' datetime='2024-03-20T12:00:00+00:00'></time>
    <div class='event-location'><h3>Test Location</h3><p>123 Main St</p></div>
    <img class='event-cover' src='https://example.com/image.jpg'/>
    <a class='ticket-link' href='https://tickets.com/event'></a>
    </body></html>
    """
    with patch("pasito_event_scripts.create_fb_event.setup_logging") as mock_setup_logging, \
         patch("pasito_event_scripts.create_fb_event.setup_driver") as mock_setup_driver, \
         patch("pasito_event_scripts.create_fb_event.login_to_facebook") as mock_login, \
         patch("pasito_event_scripts.create_fb_event.create_facebook_event") as mock_create_event, \
         patch("requests.get") as mock_requests_get, \
         patch.dict(os.environ, {
             "FB_EMAIL": "test@example.com",
             "FB_PASSWORD": "test_password",
             "FB_GROUP_ID": "123456789"
         }):
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_driver = MagicMock()
        mock_setup_driver.return_value = mock_driver
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = fake_html
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        main([test_url])
        mock_setup_logging.assert_called_once()
        mock_setup_driver.assert_called_once()
        mock_login.assert_called_once()
        mock_create_event.assert_called_once()
        mock_driver.quit.assert_called_once()

def test_main_function_error():
    """Test the main function with error handling."""
    test_url = "https://example.com/event"
    with patch("pasito_event_scripts.create_fb_event.setup_logging") as mock_setup_logging, \
         patch("pasito_event_scripts.create_fb_event.setup_driver") as mock_setup_driver, \
         patch("pasito_event_scripts.create_fb_event.login_to_facebook", side_effect=Exception("Test error")):
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_driver = MagicMock()
        mock_setup_driver.return_value = mock_driver
        with pytest.raises(SystemExit) as excinfo:
            main([test_url])
        assert excinfo.value.code == 1
        mock_logger.error.assert_called_once_with("An error occurred: %s", "Test error")
        mock_driver.quit.assert_called_once()
