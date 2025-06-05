import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import re
from pasito_event_scraper import (
    extract_series_id, 
    parse_time_to_iso8601, 
    extract_event_times,
    extract_venue_info,
    extract_event_data
)


class TestPasitoEventScraper:
    """Test cases for Pasito event scraper utility functions"""
    
    def test_extract_series_id_from_url(self):
        """Test extracting series ID from full URL"""
        url = "https://pasito.fun/boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        result = extract_series_id(url)
        assert result == "boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
    
    def test_extract_series_id_from_id(self):
        """Test extracting series ID from just the ID"""
        series_id = "boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        result = extract_series_id(series_id)
        assert result == "boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
    
    def test_extract_series_id_with_at_symbol(self):
        """Test extracting series ID with @ symbol in URL"""
        url = "https://pasito.fun/@boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        result = extract_series_id(url)
        # The function returns the last part of the URL, which includes the @
        assert result == "@boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
    
    def test_extract_series_id_empty_input(self):
        """Test extracting series ID with empty input"""
        result = extract_series_id("")
        assert result is None
    
    def test_parse_time_to_iso8601_basic(self):
        """Test basic time parsing to ISO 8601 format"""
        time_str = "Thu, Jun 5 6:30 PM"
        result = parse_time_to_iso8601(time_str)
        # Check that it contains expected elements
        assert "2025-06-05T18:30:00" in result
        assert "-06:00" in result  # Mountain Time offset
    
    def test_parse_time_to_iso8601_with_start_date(self):
        """Test time parsing with start date context"""
        start_time = "Thu, Jun 5 6:30 PM"
        end_time = "11:00 PM"
        result = parse_time_to_iso8601(end_time, start_time)
        assert "2025-06-05T23:00:00" in result
        assert "-06:00" in result
    
    def test_parse_time_to_iso8601_invalid_input(self):
        """Test time parsing with invalid input"""
        result = parse_time_to_iso8601("invalid time")
        # Function returns original string when parsing fails
        assert result == "invalid time"


class TestHTMLParsing:
    """Test cases for HTML parsing functionality using real Pasito event page structure"""
    
    @pytest.fixture
    def sample_event_html(self):
        """Sample HTML structure from actual Pasito event page"""
        return """
        <title data-suffix=" · Pasito">Boulder Salsa, Bachata, Rueda, &amp; WC Swing Social · Pasito</title>
        <meta name="description" content="Join us for an evening of dancing! Salsa, Bachata, Rueda de Casino, and West Coast Swing social dancing.">
        <h3 class="text-lg font-semibold text-gray-900 sm:text-xl">
            Boulder Salsa, Bachata, Rueda, &amp; WC Swing Social
        </h3>
        <div class="mt-2 text-sm text-gray-600">
            <p>Thu, Jun 5 6:30 PM — 11:00 PM</p>
        </div>
        <p class="mt-1 text-sm text-gray-600">
            <a href="/venues/the-avalon-ballroom-fs36m" class="hover:underline">
                The Avalon Ballroom
            </a>
        </p>
        """
    
    def test_extract_event_times_from_real_html(self, sample_event_html):
        """Test extracting event times from real HTML structure"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        
        # Find time information
        time_div = soup.find('div', class_='mt-2 text-sm text-gray-600')
        assert time_div is not None
        
        time_text = time_div.find('p').get_text().strip()
        assert "Thu, Jun 5 6:30 PM — 11:00 PM" in time_text
    
    def test_extract_venue_info_from_real_html(self, sample_event_html):
        """Test extracting venue information from real HTML structure"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        
        # Find venue link
        venue_link = soup.find('a', href=re.compile(r'/venues/'))
        assert venue_link is not None
        assert venue_link.get_text().strip() == "The Avalon Ballroom"
        assert "the-avalon-ballroom-fs36m" in venue_link['href']
    
    def test_extract_event_name_from_title(self, sample_event_html):
        """Test extracting event name from title tag"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        
        title_tag = soup.find('title')
        assert title_tag is not None
        
        # Extract event name by removing the suffix
        title_text = title_tag.get_text()
        event_name = title_text.replace(' · Pasito', '')
        assert event_name == "Boulder Salsa, Bachata, Rueda, & WC Swing Social"
    
    def test_extract_event_name_from_h3(self, sample_event_html):
        """Test extracting event name from h3 tag"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        
        h3_tag = soup.find('h3')
        assert h3_tag is not None
        
        event_name = h3_tag.get_text().strip()
        assert event_name == "Boulder Salsa, Bachata, Rueda, & WC Swing Social"
    
    def test_extract_description_from_meta(self, sample_event_html):
        """Test extracting description from meta tags"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        assert meta_desc is not None
        
        description = meta_desc.get('content')
        assert "Join us for an evening of dancing!" in description
        assert "Salsa, Bachata, Rueda de Casino" in description
    
    def test_venue_link_pattern_matching(self, sample_event_html):
        """Test regex pattern for venue link matching"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        
        # Test the regex pattern used in the main script
        venue_pattern = re.compile(r'/venues/([^"]*)')
        venue_links = soup.find_all('a', href=venue_pattern)
        
        assert len(venue_links) == 1
        assert venue_links[0].get_text().strip() == "The Avalon Ballroom"
        
        # Test extracting venue ID from href
        href = venue_links[0]['href']
        match = venue_pattern.search(href)
        assert match is not None
        assert match.group(1) == "the-avalon-ballroom-fs36m" 