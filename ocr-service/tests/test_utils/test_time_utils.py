#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the time_utils.py module.

This module contains tests for timestamp generation, date comparison, duration calculation,
and time formatting functions to ensure consistent timestamp handling in logs, message
publishing, and document metadata.
"""

import datetime
import time
from unittest.mock import patch, MagicMock
from dateutil import tz
from dateutil.relativedelta import relativedelta
import pytest

from src.utils import time_utils


class TestTimestampGeneration:
    """Tests for timestamp generation functions."""

    def test_get_current_timestamp(self):
        """Test getting the current timestamp with timezone information."""
        # Get current timestamp
        timestamp = time_utils.get_current_timestamp()
        
        # Verify it's a datetime object
        assert isinstance(timestamp, datetime.datetime)
        
        # Verify it has timezone information
        assert timestamp.tzinfo is not None
        
        # Verify it's close to the current time
        now = datetime.datetime.now(tz.tzlocal())
        diff = abs((now - timestamp).total_seconds())
        assert diff < 1.0  # Should be less than 1 second difference

    def test_get_utc_timestamp(self):
        """Test getting the current UTC timestamp."""
        # Get UTC timestamp
        timestamp = time_utils.get_utc_timestamp()
        
        # Verify it's a datetime object
        assert isinstance(timestamp, datetime.datetime)
        
        # Verify it has UTC timezone
        assert timestamp.tzinfo is not None
        assert timestamp.tzinfo == tz.UTC
        
        # Verify it's close to the current UTC time
        now = datetime.datetime.now(tz.UTC)
        diff = abs((now - timestamp).total_seconds())
        assert diff < 1.0  # Should be less than 1 second difference

    def test_get_timestamp_ms(self):
        """Test getting a timestamp in milliseconds."""
        # Test with no arguments (current time)
        ms_timestamp = time_utils.get_timestamp_ms()
        
        # Verify it's an integer
        assert isinstance(ms_timestamp, int)
        
        # Verify it's close to the current time in milliseconds
        now_ms = int(time.time() * 1000)
        diff = abs(now_ms - ms_timestamp)
        assert diff < 1000  # Should be less than 1 second difference
        
        # Test with a specific datetime
        test_dt = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        ms_timestamp = time_utils.get_timestamp_ms(test_dt)
        
        # Verify it matches the expected timestamp
        expected_ms = int(test_dt.timestamp() * 1000)
        assert ms_timestamp == expected_ms
        
        # Test with an invalid date
        assert time_utils.get_timestamp_ms("invalid_date") == 0

    def test_get_log_timestamp(self):
        """Test getting a formatted timestamp for logging purposes."""
        # Get log timestamp
        log_timestamp = time_utils.get_log_timestamp()
        
        # Verify it's a string
        assert isinstance(log_timestamp, str)
        
        # Verify it matches the expected format (YYYY-MM-DD HH:MM:SS.ffffff)
        # This is a basic format check, not checking the actual values
        assert len(log_timestamp) >= 19  # At least YYYY-MM-DD HH:MM:SS
        assert log_timestamp[4] == '-' and log_timestamp[7] == '-'  # Date separators
        assert log_timestamp[10] == ' '  # Space between date and time
        assert log_timestamp[13] == ':' and log_timestamp[16] == ':'  # Time separators


class TestDateValidationAndConversion:
    """Tests for date validation and conversion functions."""

    def test_is_valid_date(self):
        """Test checking if a date is valid."""
        # Test with valid dates in different formats
        assert time_utils.is_valid_date(datetime.datetime.now()) is True
        assert time_utils.is_valid_date("2025-05-23T12:00:00Z") is True
        assert time_utils.is_valid_date(time.time()) is True
        
        # Test with invalid dates
        assert time_utils.is_valid_date(None) is False
        assert time_utils.is_valid_date("invalid_date") is False
        assert time_utils.is_valid_date("2025-13-45") is False  # Invalid month and day
        assert time_utils.is_valid_date({}) is False  # Invalid type

    def test_to_datetime(self):
        """Test converting various date formats to a datetime object."""
        # Test with datetime object
        dt = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        assert time_utils.to_datetime(dt) == dt
        
        # Test with timestamp (float/int)
        timestamp = dt.timestamp()
        converted_dt = time_utils.to_datetime(timestamp)
        assert isinstance(converted_dt, datetime.datetime)
        assert abs((converted_dt.timestamp() - timestamp)) < 0.001  # Allow small floating point difference
        
        # Test with ISO 8601 string
        iso_str = "2025-05-23T12:00:00Z"
        converted_dt = time_utils.to_datetime(iso_str)
        assert isinstance(converted_dt, datetime.datetime)
        assert converted_dt.year == 2025
        assert converted_dt.month == 5
        assert converted_dt.day == 23
        assert converted_dt.hour == 12
        assert converted_dt.minute == 0
        assert converted_dt.second == 0
        assert converted_dt.tzinfo is not None  # Should have timezone info
        
        # Test with other date string formats
        date_str = "May 23, 2025"
        converted_dt = time_utils.to_datetime(date_str)
        assert isinstance(converted_dt, datetime.datetime)
        assert converted_dt.year == 2025
        assert converted_dt.month == 5
        assert converted_dt.day == 23
        
        # Test with invalid date
        assert time_utils.to_datetime("invalid_date") is None
        assert time_utils.to_datetime(None) is None


class TestDateComparison:
    """Tests for date comparison functions."""

    def test_is_between(self):
        """Test checking if a date is between two other dates (inclusive)."""
        # Create test dates
        start = datetime.datetime(2025, 5, 1, tzinfo=tz.UTC)
        middle = datetime.datetime(2025, 5, 15, tzinfo=tz.UTC)
        end = datetime.datetime(2025, 5, 31, tzinfo=tz.UTC)
        
        # Test date in the middle of the range
        assert time_utils.is_between(middle, start, end) is True
        
        # Test with the start date (inclusive)
        assert time_utils.is_between(start, start, end) is True
        
        # Test with the end date (inclusive)
        assert time_utils.is_between(end, start, end) is True
        
        # Test with date before the range
        before = datetime.datetime(2025, 4, 30, tzinfo=tz.UTC)
        assert time_utils.is_between(before, start, end) is False
        
        # Test with date after the range
        after = datetime.datetime(2025, 6, 1, tzinfo=tz.UTC)
        assert time_utils.is_between(after, start, end) is False
        
        # Test with different date formats
        assert time_utils.is_between("2025-05-15", "2025-05-01", "2025-05-31") is True
        assert time_utils.is_between(middle.timestamp(), start.timestamp(), end.timestamp()) is True
        
        # Test with invalid dates
        assert time_utils.is_between("invalid", start, end) is False
        assert time_utils.is_between(middle, "invalid", end) is False
        assert time_utils.is_between(middle, start, "invalid") is False

    def test_is_after(self):
        """Test checking if date1 is after date2."""
        # Create test dates
        earlier = datetime.datetime(2025, 5, 1, tzinfo=tz.UTC)
        later = datetime.datetime(2025, 5, 15, tzinfo=tz.UTC)
        
        # Test with later date first (should be True)
        assert time_utils.is_after(later, earlier) is True
        
        # Test with earlier date first (should be False)
        assert time_utils.is_after(earlier, later) is False
        
        # Test with same date (should be False)
        assert time_utils.is_after(earlier, earlier) is False
        
        # Test with different date formats
        assert time_utils.is_after("2025-05-15", "2025-05-01") is True
        assert time_utils.is_after(later.timestamp(), earlier.timestamp()) is True
        
        # Test with invalid dates
        assert time_utils.is_after("invalid", earlier) is False
        assert time_utils.is_after(later, "invalid") is False

    def test_is_same(self):
        """Test checking if two dates are the same at the specified unit level."""
        # Create test dates
        date1 = datetime.datetime(2025, 5, 15, 10, 30, 45, tzinfo=tz.UTC)
        
        # Same exact datetime
        date2 = datetime.datetime(2025, 5, 15, 10, 30, 45, tzinfo=tz.UTC)
        assert time_utils.is_same(date1, date2) is True  # Default unit is 'day'
        assert time_utils.is_same(date1, date2, 'year') is True
        assert time_utils.is_same(date1, date2, 'month') is True
        assert time_utils.is_same(date1, date2, 'day') is True
        assert time_utils.is_same(date1, date2, 'hour') is True
        assert time_utils.is_same(date1, date2, 'minute') is True
        assert time_utils.is_same(date1, date2, 'second') is True
        
        # Same day, different time
        date3 = datetime.datetime(2025, 5, 15, 14, 45, 30, tzinfo=tz.UTC)
        assert time_utils.is_same(date1, date3) is True  # Default unit is 'day'
        assert time_utils.is_same(date1, date3, 'year') is True
        assert time_utils.is_same(date1, date3, 'month') is True
        assert time_utils.is_same(date1, date3, 'day') is True
        assert time_utils.is_same(date1, date3, 'hour') is False
        assert time_utils.is_same(date1, date3, 'minute') is False
        assert time_utils.is_same(date1, date3, 'second') is False
        
        # Same month, different day
        date4 = datetime.datetime(2025, 5, 20, 10, 30, 45, tzinfo=tz.UTC)
        assert time_utils.is_same(date1, date4) is False  # Default unit is 'day'
        assert time_utils.is_same(date1, date4, 'year') is True
        assert time_utils.is_same(date1, date4, 'month') is True
        assert time_utils.is_same(date1, date4, 'day') is False
        
        # Same year, different month
        date5 = datetime.datetime(2025, 6, 15, 10, 30, 45, tzinfo=tz.UTC)
        assert time_utils.is_same(date1, date5) is False  # Default unit is 'day'
        assert time_utils.is_same(date1, date5, 'year') is True
        assert time_utils.is_same(date1, date5, 'month') is False
        
        # Different year
        date6 = datetime.datetime(2026, 5, 15, 10, 30, 45, tzinfo=tz.UTC)
        assert time_utils.is_same(date1, date6) is False  # Default unit is 'day'
        assert time_utils.is_same(date1, date6, 'year') is False
        
        # Test with different date formats
        assert time_utils.is_same("2025-05-15", "2025-05-15") is True
        assert time_utils.is_same("2025-05-15", "2025-05-16") is False
        
        # Test with invalid unit
        assert time_utils.is_same(date1, date2, 'invalid_unit') is False
        
        # Test with invalid dates
        assert time_utils.is_same("invalid", date2) is False
        assert time_utils.is_same(date1, "invalid") is False


class TestDurationCalculation:
    """Tests for duration calculation functions."""

    def test_add_time(self):
        """Test adding a duration to the current time."""
        # Mock current time to have a fixed reference point
        fixed_now = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.tzlocal())
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            
            # Test adding days
            result = time_utils.add_time({'days': 5})
            expected = fixed_now + datetime.timedelta(days=5)
            assert result.year == expected.year
            assert result.month == expected.month
            assert result.day == expected.day
            
            # Test adding a complex duration
            result = time_utils.add_time({
                'years': 1,
                'months': 2,
                'days': 3,
                'hours': 4,
                'minutes': 5,
                'seconds': 6
            })
            expected = fixed_now + relativedelta(
                years=1,
                months=2,
                days=3,
                hours=4,
                minutes=5,
                seconds=6
            )
            assert result.year == expected.year
            assert result.month == expected.month
            assert result.day == expected.day
            assert result.hour == expected.hour
            assert result.minute == expected.minute
            assert result.second == expected.second

    def test_subtract_time(self):
        """Test subtracting a duration from the current time."""
        # Mock current time to have a fixed reference point
        fixed_now = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.tzlocal())
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            
            # Test subtracting days
            result = time_utils.subtract_time({'days': 5})
            expected = fixed_now - datetime.timedelta(days=5)
            assert result.year == expected.year
            assert result.month == expected.month
            assert result.day == expected.day
            
            # Test subtracting a complex duration
            result = time_utils.subtract_time({
                'years': 1,
                'months': 2,
                'days': 3,
                'hours': 4,
                'minutes': 5,
                'seconds': 6
            })
            expected = fixed_now - relativedelta(
                years=1,
                months=2,
                days=3,
                hours=4,
                minutes=5,
                seconds=6
            )
            assert result.year == expected.year
            assert result.month == expected.month
            assert result.day == expected.day
            assert result.hour == expected.hour
            assert result.minute == expected.minute
            assert result.second == expected.second

    def test_calculate_duration(self):
        """Test calculating the duration between two timestamps in seconds."""
        # Create test timestamps
        start = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        end = datetime.datetime(2025, 5, 23, 12, 1, 30, tzinfo=tz.UTC)  # 1 minute 30 seconds later
        
        # Calculate duration
        duration = time_utils.calculate_duration(start, end)
        
        # Verify it's the expected duration (90 seconds)
        assert duration == 90.0
        
        # Test with end_time not provided (should use current time)
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 23, 12, 1, 30, tzinfo=tz.tzlocal())
            mock_datetime.now.return_value = mock_now
            
            duration = time_utils.calculate_duration(start)
            assert duration == 90.0
        
        # Test with different timezone in start and end
        start_pst = datetime.datetime(2025, 5, 23, 5, 0, 0, tzinfo=tz.gettz('America/Los_Angeles'))
        end_est = datetime.datetime(2025, 5, 23, 9, 1, 30, tzinfo=tz.gettz('America/New_York'))
        # The difference should be 1 hour 30 seconds (3600 + 90 = 3690 seconds)
        # PST is 3 hours behind EST, so 9:00 EST - 5:00 PST = 1 hour difference
        duration = time_utils.calculate_duration(start_pst, end_est)
        assert abs(duration - 3690.0) < 1.0  # Allow small difference due to DST variations
        
        # Test with string timestamps
        duration = time_utils.calculate_duration("2025-05-23T12:00:00Z", "2025-05-23T12:01:30Z")
        assert duration == 90.0
        
        # Test with invalid start time
        assert time_utils.calculate_duration("invalid", end) == 0.0
        
        # Test with invalid end time
        assert time_utils.calculate_duration(start, "invalid") == 0.0

    def test_calculate_processing_time(self):
        """Test calculating processing time metrics between two timestamps."""
        # Create test timestamps
        start = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        end = datetime.datetime(2025, 5, 23, 12, 1, 30, tzinfo=tz.UTC)  # 1 minute 30 seconds later
        
        # Calculate processing time
        result = time_utils.calculate_processing_time(start, end)
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert 'total_seconds' in result
        assert 'formatted_time' in result
        assert 'start_iso' in result
        assert 'end_iso' in result
        
        # Verify the values
        assert result['total_seconds'] == 90.0
        assert result['formatted_time'] == '1m 30s'
        assert result['start_iso'] == start.isoformat()
        assert result['end_iso'] == end.isoformat()
        
        # Test with longer duration (hours)
        end_hours = datetime.datetime(2025, 5, 23, 15, 30, 45, tzinfo=tz.UTC)  # 3 hours 30 minutes 45 seconds later
        result = time_utils.calculate_processing_time(start, end_hours)
        assert result['total_seconds'] == 12645.0  # 3*3600 + 30*60 + 45 = 12645
        assert result['formatted_time'] == '3h 30m 45s'
        
        # Test with end_time not provided (should use current time)
        with patch('datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2025, 5, 23, 12, 1, 30, tzinfo=tz.tzlocal())
            mock_datetime.now.return_value = mock_now
            
            result = time_utils.calculate_processing_time(start)
            assert abs(result['total_seconds'] - 90.0) < 1.0  # Allow small difference due to timezone handling
        
        # Test with invalid start time
        result = time_utils.calculate_processing_time("invalid", end)
        assert result['total_seconds'] == 0.0
        assert result['formatted_time'] == '0s'
        assert result['start_iso'] == 'Invalid date'
        assert result['end_iso'] == 'Invalid date'
        
        # Test with invalid end time
        result = time_utils.calculate_processing_time(start, "invalid")
        assert result['total_seconds'] == 0.0
        assert result['formatted_time'] == '0s'
        assert result['start_iso'] == start.isoformat()
        assert result['end_iso'] == 'Invalid date'

    def test_calculate_age(self):
        """Test calculating the age (time ago) of a timestamp in a human-readable format."""
        # Mock current time to have a fixed reference point
        fixed_now = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            
            # Test with various time differences
            
            # Just now (less than 10 seconds)
            date = datetime.datetime(2025, 5, 23, 11, 59, 55, tzinfo=tz.UTC)  # 5 seconds ago
            assert time_utils.calculate_age(date) == 'just now'
            
            # Seconds
            date = datetime.datetime(2025, 5, 23, 11, 59, 30, tzinfo=tz.UTC)  # 30 seconds ago
            assert time_utils.calculate_age(date) == '30 seconds ago'
            
            # Minutes
            date = datetime.datetime(2025, 5, 23, 11, 58, 0, tzinfo=tz.UTC)  # 2 minutes ago
            assert time_utils.calculate_age(date) == '2 minutes ago'
            
            # Single minute (test singular form)
            date = datetime.datetime(2025, 5, 23, 11, 59, 0, tzinfo=tz.UTC)  # 1 minute ago
            assert time_utils.calculate_age(date) == '1 minute ago'
            
            # Hours
            date = datetime.datetime(2025, 5, 23, 10, 0, 0, tzinfo=tz.UTC)  # 2 hours ago
            assert time_utils.calculate_age(date) == '2 hours ago'
            
            # Single hour (test singular form)
            date = datetime.datetime(2025, 5, 23, 11, 0, 0, tzinfo=tz.UTC)  # 1 hour ago
            assert time_utils.calculate_age(date) == '1 hour ago'
            
            # Days
            date = datetime.datetime(2025, 5, 21, 12, 0, 0, tzinfo=tz.UTC)  # 2 days ago
            assert time_utils.calculate_age(date) == '2 days ago'
            
            # Single day (test singular form)
            date = datetime.datetime(2025, 5, 22, 12, 0, 0, tzinfo=tz.UTC)  # 1 day ago
            assert time_utils.calculate_age(date) == '1 day ago'
            
            # Weeks
            date = datetime.datetime(2025, 5, 9, 12, 0, 0, tzinfo=tz.UTC)  # 2 weeks ago
            assert time_utils.calculate_age(date) == '2 weeks ago'
            
            # Single week (test singular form)
            date = datetime.datetime(2025, 5, 16, 12, 0, 0, tzinfo=tz.UTC)  # 1 week ago
            assert time_utils.calculate_age(date) == '1 week ago'
            
            # Months
            date = datetime.datetime(2025, 3, 23, 12, 0, 0, tzinfo=tz.UTC)  # 2 months ago
            assert time_utils.calculate_age(date) == '2 months ago'
            
            # Single month (test singular form)
            date = datetime.datetime(2025, 4, 23, 12, 0, 0, tzinfo=tz.UTC)  # 1 month ago
            assert time_utils.calculate_age(date) == '1 month ago'
            
            # Years
            date = datetime.datetime(2023, 5, 23, 12, 0, 0, tzinfo=tz.UTC)  # 2 years ago
            assert time_utils.calculate_age(date) == '2 years ago'
            
            # Single year (test singular form)
            date = datetime.datetime(2024, 5, 23, 12, 0, 0, tzinfo=tz.UTC)  # 1 year ago
            assert time_utils.calculate_age(date) == '1 year ago'
        
        # Test with invalid date
        assert time_utils.calculate_age("invalid") == 'Invalid date'


class TestTimeFormatting:
    """Tests for time formatting functions."""

    def test_format_datetime(self):
        """Test formatting a date as a datetime string."""
        # Create test date
        dt = datetime.datetime(2025, 5, 23, 14, 30, 0, tzinfo=tz.UTC)
        
        # Test with default format
        formatted = time_utils.format_datetime(dt)
        assert formatted == '23 May 2025 02:30 PM'
        
        # Test with custom format
        formatted = time_utils.format_datetime(dt, '%Y-%m-%d %H:%M:%S')
        assert formatted == '2025-05-23 14:30:00'
        
        # Test with string date
        formatted = time_utils.format_datetime("2025-05-23T14:30:00Z")
        assert formatted == '23 May 2025 02:30 PM'
        
        # Test with timestamp
        formatted = time_utils.format_datetime(dt.timestamp())
        assert formatted == '23 May 2025 02:30 PM'
        
        # Test with invalid date
        assert time_utils.format_datetime("invalid") == 'Invalid date'

    def test_format_date(self):
        """Test formatting a date as a date string (without time)."""
        # Create test date
        dt = datetime.datetime(2025, 5, 23, 14, 30, 0, tzinfo=tz.UTC)
        
        # Test with default format
        formatted = time_utils.format_date(dt)
        assert formatted == '23 May 2025'
        
        # Test with custom format
        formatted = time_utils.format_date(dt, '%Y-%m-%d')
        assert formatted == '2025-05-23'
        
        # Test with string date
        formatted = time_utils.format_date("2025-05-23T14:30:00Z")
        assert formatted == '23 May 2025'
        
        # Test with timestamp
        formatted = time_utils.format_date(dt.timestamp())
        assert formatted == '23 May 2025'
        
        # Test with invalid date
        assert time_utils.format_date("invalid") == 'Invalid date'

    def test_format_time(self):
        """Test formatting a date as a time string (without date)."""
        # Create test date
        dt = datetime.datetime(2025, 5, 23, 14, 30, 0, tzinfo=tz.UTC)
        
        # Test with default format
        formatted = time_utils.format_time(dt)
        assert formatted == '02:30 PM'
        
        # Test with custom format
        formatted = time_utils.format_time(dt, '%H:%M:%S')
        assert formatted == '14:30:00'
        
        # Test with string date
        formatted = time_utils.format_time("2025-05-23T14:30:00Z")
        assert formatted == '02:30 PM'
        
        # Test with timestamp
        formatted = time_utils.format_time(dt.timestamp())
        assert formatted == '02:30 PM'
        
        # Test with invalid date
        assert time_utils.format_time("invalid") == 'Invalid date'

    def test_format_iso8601(self):
        """Test formatting a date as an ISO 8601 string."""
        # Create test date
        dt = datetime.datetime(2025, 5, 23, 14, 30, 0, tzinfo=tz.UTC)
        
        # Test with datetime with timezone
        formatted = time_utils.format_iso8601(dt)
        assert formatted == '2025-05-23T14:30:00+00:00'
        
        # Test with datetime without timezone (should add UTC)
        dt_no_tz = datetime.datetime(2025, 5, 23, 14, 30, 0)  # No timezone
        formatted = time_utils.format_iso8601(dt_no_tz)
        assert formatted == '2025-05-23T14:30:00+00:00'
        
        # Test with string date
        formatted = time_utils.format_iso8601("2025-05-23T14:30:00Z")
        assert formatted == '2025-05-23T14:30:00+00:00'
        
        # Test with timestamp
        formatted = time_utils.format_iso8601(dt.timestamp())
        assert formatted == '2025-05-23T14:30:00+00:00'
        
        # Test with invalid date
        assert time_utils.format_iso8601("invalid") == 'Invalid date'

    def test_format_date_range(self):
        """Test formatting a date range as a string."""
        # Create test dates
        start = datetime.datetime(2025, 5, 15, tzinfo=tz.UTC)
        end = datetime.datetime(2025, 5, 20, tzinfo=tz.UTC)
        
        # Test with default format (not initial)
        formatted = time_utils.format_date_range(start, end)
        assert formatted == '15 - 20 May 2025'
        
        # Test with initial=True (always show full range)
        formatted = time_utils.format_date_range(start, end, initial=True)
        assert formatted == '15 May 2025 - 20 May 2025'
        
        # Test with same day
        same_day_end = datetime.datetime(2025, 5, 15, 23, 59, 59, tzinfo=tz.UTC)
        formatted = time_utils.format_date_range(start, same_day_end)
        assert formatted == '15 May 2025'
        
        # Test with same month, different year
        diff_year_end = datetime.datetime(2026, 5, 15, tzinfo=tz.UTC)
        formatted = time_utils.format_date_range(start, diff_year_end)
        assert formatted == '15 May 2025 - 15 May 2026'
        
        # Test with different month, same year
        diff_month_end = datetime.datetime(2025, 6, 15, tzinfo=tz.UTC)
        formatted = time_utils.format_date_range(start, diff_month_end)
        assert formatted == '15 May - 15 Jun 2025'
        
        # Test with string dates
        formatted = time_utils.format_date_range("2025-05-15", "2025-05-20")
        assert formatted == '15 - 20 May 2025'
        
        # Test with invalid dates
        assert time_utils.format_date_range("invalid", end) == 'Invalid date'
        assert time_utils.format_date_range(start, "invalid") == 'Invalid date'
        
        # Test with end date before start date
        assert time_utils.format_date_range(end, start) == 'Invalid date'


class TestTimezoneHandling:
    """Tests for timezone handling consistency."""

    def test_timezone_consistency(self):
        """Test that timezone information is consistently handled across functions."""
        # Create dates with different timezone representations
        utc_date = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        est_date = datetime.datetime(2025, 5, 23, 8, 0, 0, tzinfo=tz.gettz('America/New_York'))
        pst_date = datetime.datetime(2025, 5, 23, 5, 0, 0, tzinfo=tz.gettz('America/Los_Angeles'))
        
        # These dates represent the same moment in time, just in different timezones
        # Verify that format_iso8601 produces consistent results
        utc_iso = time_utils.format_iso8601(utc_date)
        est_iso = time_utils.format_iso8601(est_date)
        pst_iso = time_utils.format_iso8601(pst_date)
        
        # Convert back to datetime and verify they represent the same moment
        utc_dt = time_utils.to_datetime(utc_iso)
        est_dt = time_utils.to_datetime(est_iso)
        pst_dt = time_utils.to_datetime(pst_iso)
        
        # All should be within a second of each other when converted to UTC
        assert abs((utc_dt - est_dt).total_seconds()) < 1.0
        assert abs((utc_dt - pst_dt).total_seconds()) < 1.0
        
        # Test that calculate_duration handles timezone differences correctly
        duration_utc_est = time_utils.calculate_duration(utc_date, est_date)
        duration_est_pst = time_utils.calculate_duration(est_date, pst_date)
        
        # The duration should be close to zero since they represent the same moment
        assert abs(duration_utc_est) < 1.0
        assert abs(duration_est_pst) < 1.0

    def test_timezone_conversion(self):
        """Test that timezone conversion is handled correctly."""
        # Create a date in UTC
        utc_date = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        
        # Convert to string and back, should preserve timezone
        iso_str = time_utils.format_iso8601(utc_date)
        converted = time_utils.to_datetime(iso_str)
        
        # Verify timezone is preserved
        assert converted.tzinfo is not None
        
        # Verify the time is the same
        assert abs((utc_date - converted).total_seconds()) < 1.0
        
        # Test with a date without timezone (should default to UTC)
        naive_date = datetime.datetime(2025, 5, 23, 12, 0, 0)  # No timezone
        iso_str = time_utils.format_iso8601(naive_date)
        converted = time_utils.to_datetime(iso_str)
        
        # Verify timezone is added
        assert converted.tzinfo is not None
        
        # Verify the time is interpreted as UTC
        utc_equivalent = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.UTC)
        assert abs((utc_equivalent - converted).total_seconds()) < 1.0


class TestDocumentMetadata:
    """Tests for document metadata functions."""

    def test_get_document_processing_metadata(self):
        """Test generating document processing metadata with timestamps."""
        # Mock current time to have a fixed reference point
        fixed_now = datetime.datetime(2025, 5, 23, 12, 1, 30, tzinfo=tz.tzlocal())
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            
            # Create a start time 90 seconds earlier
            start_time = datetime.datetime(2025, 5, 23, 12, 0, 0, tzinfo=tz.tzlocal())
            
            # Generate metadata
            metadata = time_utils.get_document_processing_metadata(start_time)
            
            # Verify the metadata structure
            assert isinstance(metadata, dict)
            assert 'processing_started' in metadata
            assert 'processing_completed' in metadata
            assert 'processing_duration_seconds' in metadata
            assert 'processing_duration_formatted' in metadata
            assert 'timestamp' in metadata
            
            # Verify the values
            assert metadata['processing_started'] == time_utils.format_iso8601(start_time)
            assert metadata['processing_completed'] == time_utils.format_iso8601(fixed_now)
            assert metadata['processing_duration_seconds'] == '90.0'
            assert metadata['processing_duration_formatted'] == '1m 30s'
            assert metadata['timestamp'] == time_utils.format_iso8601(fixed_now)
            
            # Test with invalid start time (should use current time as start)
            metadata = time_utils.get_document_processing_metadata("invalid")
            assert metadata['processing_started'] == time_utils.format_iso8601(fixed_now)
            assert metadata['processing_duration_seconds'] == '0.0'
            assert metadata['processing_duration_formatted'] == '0.00s'