import pytest
from bs4 import BeautifulSoup
from pasito_event_scraper import (
    extract_series_id, 
    parse_time_to_iso8601, 
    extract_event_times,
    extract_venue_info,
    extract_event_data
)


class TestPasitoEventScraper:
    """Basic tests for Pasito event scraper utility functions"""
    
    def test_extract_series_id_from_url(self):
        """Test extracting series ID from a series URL"""
        url = "https://pasito.fun/es/boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        expected = "boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        assert extract_series_id(url) == expected
    
    def test_extract_series_id_from_id(self):
        """Test extracting series ID when already an ID"""
        series_id = "boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        assert extract_series_id(series_id) == series_id
    
    def test_extract_series_id_with_at_symbol(self):
        """Test extracting series ID with @ prefix"""
        series_id = "@boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        expected = "boulder-salsa-bachata-rueda-wc-swing-social-xd9r4"
        assert extract_series_id(series_id) == expected
    
    def test_extract_series_id_empty_input(self):
        """Test extracting series ID with empty input"""
        assert extract_series_id("") is None
        assert extract_series_id(None) is None
    
    def test_parse_time_to_iso8601_basic(self):
        """Test parsing a basic time string to ISO 8601"""
        time_str = "Thu, Jun 12 6:30 PM"
        result = parse_time_to_iso8601(time_str)
        # Should contain the basic ISO format elements
        assert "2025-06-12T18:30:00" in result
        assert "-06:00" in result  # Mountain Time offset
    
    def test_parse_time_to_iso8601_with_start_date(self):
        """Test parsing end time with start date context"""
        start_time = "Thu, Jun 12 6:30 PM"
        end_time = "11:00 PM"
        result = parse_time_to_iso8601(end_time, start_time)
        # Should contain the date from start_time
        assert "2025-06-12T23:00:00" in result
        assert "-06:00" in result
    
    def test_parse_time_to_iso8601_invalid_input(self):
        """Test parsing with invalid input returns original string"""
        invalid_time = "invalid time string"
        result = parse_time_to_iso8601(invalid_time)
        assert result == invalid_time


class TestHTMLParsing:
    """Tests for HTML parsing functions using real Pasito HTML structure"""
    
    @pytest.fixture
    def sample_event_html(self):
        """Sample HTML from actual Pasito event page"""
        return """
        <title data-suffix=" · Pasito">Boulder Salsa, Bachata, Rueda, &amp; WC Swing Social · Pasito</title>
        <meta content="Every Thursday join us for a night full of dancing and a variety of classes for you to choose fro..." property="og:description">
        
        <h3 class="pc-h3 mb-0 pc-heading--color pc-heading--margin">
            <span class="hero-calendar h-5 w-5 -mt-1 lg:h-6 lg:w-6 lg:-mt-1.5 inline-block"></span> 
            Boulder Salsa, Bachata, Rueda, &amp; WC Swing Social
        </h3>
        
        <p class="pc-text pc-p--margin">
            🕘 Thu, Jun 5 6:30 PM — 11:00 PM
        </p>
        
        <p class="pc-text pc-p--margin">
            📍
            <a href="https://pasito.fun/l/the-avalon-ballroom-fs36m" class="hover:underline">
                The Avalon Ballroom
            </a>
        </p>
        """
    
    def test_extract_event_times_from_real_html(self, sample_event_html):
        """Test extracting event times from real HTML structure"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        start_time, end_time = extract_event_times(soup)
        
        assert start_time == "Thu, Jun 5 6:30 PM"
        assert end_time == "11:00 PM"
    
    def test_extract_venue_info_from_real_html(self, sample_event_html):
        """Test extracting venue information from real HTML structure"""
        venue_data = extract_venue_info(sample_event_html, None)
        
        assert "place" in venue_data
        assert venue_data["place"] == "The Avalon Ballroom"
    
    def test_extract_event_name_from_title(self, sample_event_html):
        """Test extracting event name from title tag"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        title_tag = soup.find('title')
        
        assert title_tag is not None
        title_text = title_tag.get_text().replace(' · Pasito', '').replace('&amp;', '&').strip()
        assert title_text == "Boulder Salsa, Bachata, Rueda, & WC Swing Social"
    
    def test_extract_event_name_from_h3(self, sample_event_html):
        """Test extracting event name from h3 tag"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        h3_tag = soup.find('h3', class_='pc-h3')
        
        assert h3_tag is not None
        event_name = h3_tag.get_text(strip=True).replace('&amp;', '&')
        assert "Boulder Salsa, Bachata, Rueda, & WC Swing Social" in event_name
    
    def test_extract_description_from_meta(self, sample_event_html):
        """Test extracting description from meta tags"""
        soup = BeautifulSoup(sample_event_html, 'lxml')
        meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        
        assert meta_desc is not None
        description = meta_desc.get('content')
        assert "Every Thursday join us for a night full of dancing" in description
    
    def test_venue_link_pattern_matching(self, sample_event_html):
        """Test venue link regex pattern matching"""
        import re
        
        venue_pattern = r'<a[^>]+href="(https://pasito\.fun/l/[^\"]+)"[^>]*>([^<]*)</a>'
        matches = re.findall(venue_pattern, sample_event_html, re.IGNORECASE)
        
        assert len(matches) == 1
        url, venue_name = matches[0]
        assert url == "https://pasito.fun/l/the-avalon-ballroom-fs36m"
        assert venue_name.strip() == "The Avalon Ballroom" 