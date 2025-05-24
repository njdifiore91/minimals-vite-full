#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for time utilities in the Document Service.

This module contains tests for timestamp generation, date comparison,
duration calculation, and time formatting functions to ensure consistent
timestamp handling across the Document Service.
"""

import datetime
import time
import unittest
from unittest.mock import patch, Mock
import pytest
from freezegun import freeze_time

# Import the module to test
from src.utils.time_utils import (
    get_current_timestamp,
    get_timestamp_str,
    get_timestamp_with_timezone,
    format_timestamp,
    parse_timestamp,
    format_human_readable,
    is_same_day,
    is_before,
    is_after,
    is_between,
    calculate_duration,
    format_duration,
    format_duration_short,
    calculate_age,
    format_age,
    calculate_processing_time,
    format_processing_time,
    get_timestamp_for_filename,
    convert_timezone,
    get_timezone_offset,
    add_timezone_info,
    timestamp_to_unix,
    unix_to_timestamp,
    get_document_processing_start_time,
    calculate_document_processing_time,
    format_timestamp_for_message,
    format_document_metadata_timestamp,
    format_log_timestamp,
    compare_document_timestamps,
    get_message_timestamp,
    validate_timestamp_format,
    get_document_age_category,
    get_processing_deadline,
    is_processing_overdue,
    format_time_remaining,
    ISO_8601_FORMAT,
    ISO_8601_FORMAT_WITH_TZ,
    DEFAULT_TIMEZONE
)


# Define test fixtures and constants
@pytest.fixture
def fixed_datetime():
    """Return a fixed datetime for testing."""
    return datetime.datetime(2023, 4, 15, 12, 30, 45, tzinfo=datetime.timezone.utc)


@pytest.fixture
def fixed_datetime_naive():
    """Return a fixed naive datetime for testing."""
    return datetime.datetime(2023, 4, 15, 12, 30, 45)


@pytest.fixture
def fixed_datetime_different_day():
    """Return a fixed datetime on a different day for testing."""
    return datetime.datetime(2023, 4, 16, 12, 30, 45, tzinfo=datetime.timezone.utc)


@pytest.fixture
def fixed_datetime_different_timezone():
    """Return a fixed datetime with a different timezone for testing."""
    # Create a timezone at UTC-5 (e.g., Eastern Standard Time)
    tz = datetime.timezone(datetime.timedelta(hours=-5))
    return datetime.datetime(2023, 4, 15, 7, 30, 45, tzinfo=tz)  # Same time as fixed_datetime in UTC-5


# Test timestamp generation functions
class TestTimestampGeneration:
    """Test cases for timestamp generation functions."""

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_current_timestamp(self):
        """Test that get_current_timestamp returns the current time with UTC timezone."""
        timestamp = get_current_timestamp()
        assert timestamp.year == 2023
        assert timestamp.month == 4
        assert timestamp.day == 15
        assert timestamp.hour == 12
        assert timestamp.minute == 30
        assert timestamp.second == 45
        assert timestamp.tzinfo is not None
        assert timestamp.tzinfo == datetime.timezone.utc

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_timestamp_str(self):
        """Test that get_timestamp_str returns an ISO 8601 formatted string."""
        timestamp_str = get_timestamp_str()
        assert timestamp_str == "2023-04-15T12:30:45+00:00"

    @patch("src.utils.time_utils.USING_ZONEINFO", True)
    @patch("src.utils.time_utils.ZoneInfo")
    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_timestamp_with_timezone_zoneinfo(self, mock_zoneinfo):
        """Test get_timestamp_with_timezone using ZoneInfo."""
        # Setup mock
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz

        # Call function
        timestamp = get_timestamp_with_timezone("America/New_York")

        # Assertions
        mock_zoneinfo.assert_called_once_with("America/New_York")
        assert timestamp.tzinfo == mock_tz

    @patch("src.utils.time_utils.USING_ZONEINFO", False)
    @patch("src.utils.time_utils.pytz")
    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_timestamp_with_timezone_pytz(self, mock_pytz):
        """Test get_timestamp_with_timezone using pytz."""
        # Setup mock
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz

        # Call function
        timestamp = get_timestamp_with_timezone("America/New_York")

        # Assertions
        mock_pytz.timezone.assert_called_once_with("America/New_York")
        assert timestamp.tzinfo == mock_tz

    @patch("src.utils.time_utils.USING_ZONEINFO", True)
    @patch("src.utils.time_utils.ZoneInfo", side_effect=Exception("Invalid timezone"))
    def test_get_timestamp_with_timezone_invalid(self, mock_zoneinfo):
        """Test get_timestamp_with_timezone with an invalid timezone."""
        with pytest.raises(ValueError) as excinfo:
            get_timestamp_with_timezone("Invalid/Timezone")
        assert "Invalid timezone" in str(excinfo.value)

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_timestamp_for_filename(self):
        """Test that get_timestamp_for_filename returns a properly formatted string."""
        timestamp_str = get_timestamp_for_filename()
        assert timestamp_str == "20230415_123045"


# Test timestamp formatting functions
class TestTimestampFormatting:
    """Test cases for timestamp formatting functions."""

    def test_format_timestamp(self, fixed_datetime):
        """Test that format_timestamp correctly formats a datetime object."""
        timestamp_str = format_timestamp(fixed_datetime)
        assert timestamp_str == "2023-04-15T12:30:45+00:00"

    def test_format_timestamp_no_timezone(self, fixed_datetime_naive):
        """Test that format_timestamp handles naive datetime objects."""
        # Without timezone info
        timestamp_str = format_timestamp(fixed_datetime_naive, include_timezone=False)
        assert timestamp_str == "2023-04-15T12:30:45"

        # With timezone info (should add UTC)
        timestamp_str = format_timestamp(fixed_datetime_naive, include_timezone=True)
        assert timestamp_str == "2023-04-15T12:30:45+00:00"

    def test_format_human_readable(self, fixed_datetime):
        """Test that format_human_readable correctly formats a datetime object."""
        readable_str = format_human_readable(fixed_datetime)
        assert readable_str == "2023-04-15 12:30:45"

    def test_format_log_timestamp(self, fixed_datetime):
        """Test that format_log_timestamp correctly formats a datetime object for logs."""
        log_timestamp = format_log_timestamp(fixed_datetime)
        assert log_timestamp == "2023-04-15T12:30:45.000000Z"

    def test_format_log_timestamp_current_time(self):
        """Test that format_log_timestamp works with current time."""
        with freeze_time("2023-04-15 12:30:45", tz_offset=0):
            log_timestamp = format_log_timestamp()
            assert log_timestamp == "2023-04-15T12:30:45.000000Z"

    def test_format_timestamp_for_message(self, fixed_datetime):
        """Test that format_timestamp_for_message correctly formats a datetime object."""
        message_timestamp = format_timestamp_for_message(fixed_datetime)
        assert message_timestamp == "2023-04-15T12:30:45+00:00"

    def test_format_timestamp_for_message_current_time(self):
        """Test that format_timestamp_for_message works with current time."""
        with freeze_time("2023-04-15 12:30:45", tz_offset=0):
            message_timestamp = format_timestamp_for_message()
            assert message_timestamp == "2023-04-15T12:30:45+00:00"

    def test_format_document_metadata_timestamp(self, fixed_datetime):
        """Test that format_document_metadata_timestamp correctly formats a datetime object."""
        metadata_timestamp = format_document_metadata_timestamp(fixed_datetime)
        assert metadata_timestamp == "2023-04-15T12:30:45+00:00"

    def test_format_document_metadata_timestamp_current_time(self):
        """Test that format_document_metadata_timestamp works with current time."""
        with freeze_time("2023-04-15 12:30:45", tz_offset=0):
            metadata_timestamp = format_document_metadata_timestamp()
            assert metadata_timestamp == "2023-04-15T12:30:45+00:00"


# Test timestamp parsing functions
class TestTimestampParsing:
    """Test cases for timestamp parsing functions."""

    def test_parse_timestamp_iso8601(self):
        """Test that parse_timestamp correctly parses an ISO 8601 formatted string."""
        # Test with timezone info
        dt = parse_timestamp("2023-04-15T12:30:45+00:00")
        assert dt.year == 2023
        assert dt.month == 4
        assert dt.day == 15
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45
        assert dt.tzinfo is not None
        assert dt.tzinfo == datetime.timezone.utc

    def test_parse_timestamp_with_z(self):
        """Test that parse_timestamp correctly parses an ISO 8601 string with Z timezone."""
        dt = parse_timestamp("2023-04-15T12:30:45Z")
        assert dt.year == 2023
        assert dt.month == 4
        assert dt.day == 15
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45
        assert dt.tzinfo is not None
        assert dt.tzinfo == datetime.timezone.utc

    def test_parse_timestamp_invalid(self):
        """Test that parse_timestamp raises ValueError for invalid timestamp strings."""
        with pytest.raises(ValueError) as excinfo:
            parse_timestamp("not-a-timestamp")
        assert "Invalid ISO 8601 timestamp" in str(excinfo.value)

    def test_validate_timestamp_format_valid(self):
        """Test that validate_timestamp_format returns True for valid timestamp strings."""
        assert validate_timestamp_format("2023-04-15T12:30:45+00:00") is True
        assert validate_timestamp_format("2023-04-15T12:30:45Z") is True

    def test_validate_timestamp_format_invalid(self):
        """Test that validate_timestamp_format returns False for invalid timestamp strings."""
        assert validate_timestamp_format("not-a-timestamp") is False
        assert validate_timestamp_format("2023-04-15") is False  # Missing time part


# Test date comparison functions
class TestDateComparison:
    """Test cases for date comparison functions."""

    def test_is_same_day(self, fixed_datetime, fixed_datetime_different_day):
        """Test that is_same_day correctly identifies same day datetimes."""
        # Same day, different time
        same_day_different_time = fixed_datetime.replace(hour=14, minute=45)
        assert is_same_day(fixed_datetime, same_day_different_time) is True

        # Different day
        assert is_same_day(fixed_datetime, fixed_datetime_different_day) is False

    def test_is_before(self, fixed_datetime):
        """Test that is_before correctly compares datetimes."""
        earlier = fixed_datetime.replace(hour=11)
        later = fixed_datetime.replace(hour=13)

        assert is_before(earlier, later) is True
        assert is_before(later, earlier) is False
        assert is_before(fixed_datetime, fixed_datetime) is False

    def test_is_after(self, fixed_datetime):
        """Test that is_after correctly compares datetimes."""
        earlier = fixed_datetime.replace(hour=11)
        later = fixed_datetime.replace(hour=13)

        assert is_after(later, earlier) is True
        assert is_after(earlier, later) is False
        assert is_after(fixed_datetime, fixed_datetime) is False

    def test_is_between(self, fixed_datetime):
        """Test that is_between correctly identifies datetimes within a range."""
        start = fixed_datetime.replace(hour=11)
        end = fixed_datetime.replace(hour=13)
        middle = fixed_datetime.replace(hour=12)

        # Within range
        assert is_between(middle, start, end) is True

        # At boundaries (inclusive)
        assert is_between(start, start, end) is True
        assert is_between(end, start, end) is True

        # Outside range
        before = fixed_datetime.replace(hour=10)
        after = fixed_datetime.replace(hour=14)
        assert is_between(before, start, end) is False
        assert is_between(after, start, end) is False

    def test_compare_document_timestamps(self, fixed_datetime):
        """Test that compare_document_timestamps correctly compares timestamps."""
        earlier = fixed_datetime.replace(hour=11)
        later = fixed_datetime.replace(hour=13)

        # Test with datetime objects
        assert compare_document_timestamps(earlier, later) == -1
        assert compare_document_timestamps(later, earlier) == 1
        assert compare_document_timestamps(fixed_datetime, fixed_datetime) == 0

        # Test with string timestamps
        assert compare_document_timestamps(format_timestamp(earlier), format_timestamp(later)) == -1
        assert compare_document_timestamps(format_timestamp(later), format_timestamp(earlier)) == 1
        assert compare_document_timestamps(format_timestamp(fixed_datetime), format_timestamp(fixed_datetime)) == 0

        # Test with mixed types
        assert compare_document_timestamps(earlier, format_timestamp(later)) == -1
        assert compare_document_timestamps(format_timestamp(later), earlier) == 1


# Test duration calculation functions
class TestDurationCalculation:
    """Test cases for duration calculation functions."""

    def test_calculate_duration(self, fixed_datetime):
        """Test that calculate_duration correctly calculates time differences."""
        start = fixed_datetime
        end = start + datetime.timedelta(hours=2, minutes=30, seconds=15)

        duration = calculate_duration(start, end)
        assert isinstance(duration, datetime.timedelta)
        assert duration.total_seconds() == 9015  # 2h30m15s in seconds

    def test_format_duration(self):
        """Test that format_duration correctly formats timedeltas."""
        # Test various durations
        assert format_duration(datetime.timedelta(days=2, hours=3, minutes=45)) == "2 days, 3 hours, 45 minutes"
        assert format_duration(datetime.timedelta(hours=1, minutes=30)) == "1 hour, 30 minutes"
        assert format_duration(datetime.timedelta(minutes=5, seconds=30)) == "5 minutes, 30.00 seconds"
        assert format_duration(datetime.timedelta(seconds=45)) == "45.00 seconds"
        assert format_duration(datetime.timedelta(0)) == "0.00 seconds"

    def test_format_duration_short(self):
        """Test that format_duration_short correctly formats timedeltas."""
        # Test various durations
        assert format_duration_short(datetime.timedelta(days=2, hours=3, minutes=45)) == "2d 3h 45m"
        assert format_duration_short(datetime.timedelta(hours=1, minutes=30)) == "1h 30m"
        assert format_duration_short(datetime.timedelta(minutes=5, seconds=30)) == "5m 30s"
        assert format_duration_short(datetime.timedelta(seconds=45)) == "45s"
        assert format_duration_short(datetime.timedelta(0)) == "0s"

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_calculate_age(self):
        """Test that calculate_age correctly calculates the age of a datetime."""
        # Test with a datetime 2 days ago
        dt = datetime.datetime(2023, 4, 13, 12, 30, 45, tzinfo=datetime.timezone.utc)
        age = calculate_age(dt)
        assert isinstance(age, datetime.timedelta)
        assert age.days == 2

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_format_age(self):
        """Test that format_age correctly formats the age of a datetime."""
        # Test with a datetime 2 days, 3 hours ago
        dt = datetime.datetime(2023, 4, 13, 9, 30, 45, tzinfo=datetime.timezone.utc)
        
        # Long format
        age_str = format_age(dt, short=False)
        assert "2 days, 3 hours" in age_str
        
        # Short format
        age_str_short = format_age(dt, short=True)
        assert age_str_short == "2d 3h"

    def test_calculate_processing_time(self):
        """Test that calculate_processing_time correctly calculates processing time."""
        start_time = time.time() - 1.5  # 1.5 seconds ago
        processing_time = calculate_processing_time(start_time)
        
        # Should be approximately 1.5 seconds, allow small margin for test execution time
        assert 1.4 <= processing_time <= 1.6

    def test_format_processing_time(self):
        """Test that format_processing_time correctly formats processing times."""
        # Test microseconds
        assert format_processing_time(0.000123) == "123.00 μs"
        
        # Test milliseconds
        assert format_processing_time(0.123) == "123.00 ms"
        
        # Test seconds
        assert format_processing_time(1.23) == "1.23 s"

    @patch("src.utils.time_utils.calculate_processing_time")
    def test_calculate_document_processing_time(self, mock_calculate_processing_time):
        """Test that calculate_document_processing_time correctly calculates and formats processing time."""
        mock_calculate_processing_time.return_value = 1.23
        
        processing_time, formatted_time = calculate_document_processing_time(123.45)
        
        assert processing_time == 1.23
        assert formatted_time == "1.23 s"
        mock_calculate_processing_time.assert_called_once_with(123.45)


# Test timezone handling functions
class TestTimezoneHandling:
    """Test cases for timezone handling functions."""

    @patch("src.utils.time_utils.USING_ZONEINFO", True)
    @patch("src.utils.time_utils.ZoneInfo")
    def test_convert_timezone_zoneinfo(self, mock_zoneinfo, fixed_datetime):
        """Test that convert_timezone correctly converts timezones using ZoneInfo."""
        # Setup mock
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz
        
        # Call function
        result = convert_timezone(fixed_datetime, "America/New_York")
        
        # Assertions
        mock_zoneinfo.assert_called_once_with("America/New_York")
        assert result.tzinfo == mock_tz

    @patch("src.utils.time_utils.USING_ZONEINFO", False)
    @patch("src.utils.time_utils.pytz")
    def test_convert_timezone_pytz(self, mock_pytz, fixed_datetime):
        """Test that convert_timezone correctly converts timezones using pytz."""
        # Setup mock
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz
        
        # Call function
        result = convert_timezone(fixed_datetime, "America/New_York")
        
        # Assertions
        mock_pytz.timezone.assert_called_once_with("America/New_York")
        assert result.tzinfo == mock_tz

    @patch("src.utils.time_utils.USING_ZONEINFO", True)
    @patch("src.utils.time_utils.ZoneInfo", side_effect=Exception("Invalid timezone"))
    def test_convert_timezone_invalid(self, mock_zoneinfo, fixed_datetime):
        """Test that convert_timezone raises ValueError for invalid timezones."""
        with pytest.raises(ValueError) as excinfo:
            convert_timezone(fixed_datetime, "Invalid/Timezone")
        assert "Invalid timezone" in str(excinfo.value)

    def test_convert_timezone_naive(self, fixed_datetime_naive):
        """Test that convert_timezone handles naive datetime objects."""
        with patch("src.utils.time_utils.USING_ZONEINFO", True):
            with patch("src.utils.time_utils.ZoneInfo") as mock_zoneinfo:
                mock_tz = Mock()
                mock_zoneinfo.return_value = mock_tz
                
                result = convert_timezone(fixed_datetime_naive, "America/New_York")
                
                # Should have added UTC timezone before converting
                assert result.tzinfo == mock_tz

    @patch("src.utils.time_utils.USING_ZONEINFO", True)
    @patch("src.utils.time_utils.ZoneInfo")
    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_timezone_offset(self, mock_zoneinfo):
        """Test that get_timezone_offset returns the correct timezone offset."""
        # Setup mock for EST (UTC-5)
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz
        
        # Mock the result of astimezone to return a datetime with -05:00 offset
        mock_dt = Mock()
        mock_dt.strftime.return_value = "-0500"
        
        with patch("datetime.datetime.astimezone", return_value=mock_dt):
            offset = get_timezone_offset("America/New_York")
            
            mock_zoneinfo.assert_called_once_with("America/New_York")
            assert offset == "-05:00"

    @patch("src.utils.time_utils.USING_ZONEINFO", True)
    @patch("src.utils.time_utils.ZoneInfo", side_effect=Exception("Invalid timezone"))
    def test_get_timezone_offset_invalid(self, mock_zoneinfo):
        """Test that get_timezone_offset raises ValueError for invalid timezones."""
        with pytest.raises(ValueError) as excinfo:
            get_timezone_offset("Invalid/Timezone")
        assert "Invalid timezone" in str(excinfo.value)

    @patch("src.utils.time_utils.USING_ZONEINFO", True)
    @patch("src.utils.time_utils.ZoneInfo")
    def test_add_timezone_info(self, mock_zoneinfo, fixed_datetime_naive):
        """Test that add_timezone_info correctly adds timezone information."""
        # Setup mock
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz
        
        # Call function
        result = add_timezone_info(fixed_datetime_naive, "America/New_York")
        
        # Assertions
        mock_zoneinfo.assert_called_once_with("America/New_York")
        assert result.tzinfo == mock_tz

    def test_add_timezone_info_already_aware(self, fixed_datetime):
        """Test that add_timezone_info raises ValueError for already timezone-aware datetimes."""
        with pytest.raises(ValueError) as excinfo:
            add_timezone_info(fixed_datetime, "America/New_York")
        assert "already has timezone information" in str(excinfo.value)


# Test Unix timestamp conversion functions
class TestUnixTimestampConversion:
    """Test cases for Unix timestamp conversion functions."""

    def test_timestamp_to_unix(self, fixed_datetime):
        """Test that timestamp_to_unix correctly converts a datetime to Unix timestamp."""
        # 2023-04-15 12:30:45 UTC in Unix time
        expected_unix_time = 1681562645.0
        
        unix_time = timestamp_to_unix(fixed_datetime)
        assert unix_time == expected_unix_time

    def test_timestamp_to_unix_naive(self, fixed_datetime_naive):
        """Test that timestamp_to_unix handles naive datetime objects."""
        # 2023-04-15 12:30:45 UTC in Unix time
        expected_unix_time = 1681562645.0
        
        unix_time = timestamp_to_unix(fixed_datetime_naive)
        assert unix_time == expected_unix_time

    def test_unix_to_timestamp(self):
        """Test that unix_to_timestamp correctly converts a Unix timestamp to datetime."""
        # 2023-04-15 12:30:45 UTC in Unix time
        unix_time = 1681562645.0
        
        dt = unix_to_timestamp(unix_time)
        assert dt.year == 2023
        assert dt.month == 4
        assert dt.day == 15
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45
        assert dt.tzinfo == datetime.timezone.utc


# Test document processing time functions
class TestDocumentProcessingTime:
    """Test cases for document processing time functions."""

    def test_get_document_processing_start_time(self):
        """Test that get_document_processing_start_time returns a float timestamp."""
        start_time = get_document_processing_start_time()
        assert isinstance(start_time, float)
        
        # Should be close to current time.time()
        current_time = time.time()
        assert abs(start_time - current_time) < 0.1

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_message_timestamp(self):
        """Test that get_message_timestamp returns a correctly formatted dictionary."""
        message_timestamp = get_message_timestamp()
        
        assert isinstance(message_timestamp, dict)
        assert "timestamp" in message_timestamp
        assert "unix_timestamp" in message_timestamp
        assert "timezone" in message_timestamp
        
        assert message_timestamp["timestamp"] == "2023-04-15T12:30:45+00:00"
        assert message_timestamp["unix_timestamp"] == 1681562645.0
        assert message_timestamp["timezone"] == "UTC"

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_processing_deadline(self):
        """Test that get_processing_deadline correctly calculates the deadline."""
        # Test with datetime object
        received = datetime.datetime(2023, 4, 15, 12, 25, 45, tzinfo=datetime.timezone.utc)
        deadline = get_processing_deadline(received, processing_sla_minutes=5)
        
        assert deadline.year == 2023
        assert deadline.month == 4
        assert deadline.day == 15
        assert deadline.hour == 12
        assert deadline.minute == 30
        assert deadline.second == 45
        
        # Test with string timestamp
        deadline = get_processing_deadline("2023-04-15T12:25:45Z", processing_sla_minutes=5)
        
        assert deadline.year == 2023
        assert deadline.month == 4
        assert deadline.day == 15
        assert deadline.hour == 12
        assert deadline.minute == 30
        assert deadline.second == 45

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_is_processing_overdue(self):
        """Test that is_processing_overdue correctly identifies overdue processing."""
        # Not overdue (received 3 minutes ago, SLA is 5 minutes)
        received_not_overdue = datetime.datetime(2023, 4, 15, 12, 27, 45, tzinfo=datetime.timezone.utc)
        assert is_processing_overdue(received_not_overdue, processing_sla_minutes=5) is False
        
        # Overdue (received 6 minutes ago, SLA is 5 minutes)
        received_overdue = datetime.datetime(2023, 4, 15, 12, 24, 45, tzinfo=datetime.timezone.utc)
        assert is_processing_overdue(received_overdue, processing_sla_minutes=5) is True
        
        # Test with string timestamp
        assert is_processing_overdue("2023-04-15T12:24:45Z", processing_sla_minutes=5) is True

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_format_time_remaining(self):
        """Test that format_time_remaining correctly formats the time remaining."""
        # Future deadline (1 minute from now)
        future_deadline = datetime.datetime(2023, 4, 15, 12, 31, 45, tzinfo=datetime.timezone.utc)
        remaining = format_time_remaining(future_deadline)
        assert remaining == "1 minute, 0.00 seconds"
        
        # Past deadline (overdue)
        past_deadline = datetime.datetime(2023, 4, 15, 12, 29, 45, tzinfo=datetime.timezone.utc)
        remaining = format_time_remaining(past_deadline)
        assert remaining == "Overdue"


# Test document age categorization
class TestDocumentAgeCategory:
    """Test cases for document age categorization functions."""

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_get_document_age_category(self):
        """Test that get_document_age_category correctly categorizes documents by age."""
        # New document (less than 1 day old)
        new_doc = datetime.datetime(2023, 4, 15, 10, 30, 45, tzinfo=datetime.timezone.utc)
        assert get_document_age_category(new_doc) == "new"
        
        # Recent document (less than 1 week old)
        recent_doc = datetime.datetime(2023, 4, 10, 12, 30, 45, tzinfo=datetime.timezone.utc)
        assert get_document_age_category(recent_doc) == "recent"
        
        # Old document (less than 1 month old)
        old_doc = datetime.datetime(2023, 3, 20, 12, 30, 45, tzinfo=datetime.timezone.utc)
        assert get_document_age_category(old_doc) == "old"
        
        # Archived document (1 month or older)
        archived_doc = datetime.datetime(2023, 3, 1, 12, 30, 45, tzinfo=datetime.timezone.utc)
        assert get_document_age_category(archived_doc) == "archived"
        
        # Test with string timestamp
        assert get_document_age_category("2023-04-15T10:30:45Z") == "new"


# Integration tests for multiple functions
class TestIntegration:
    """Integration tests for time utility functions."""

    @freeze_time("2023-04-15 12:30:45", tz_offset=0)
    def test_document_processing_workflow(self):
        """Test a complete document processing workflow with timestamps."""
        # 1. Document received
        received_time = get_current_timestamp()
        received_str = format_timestamp(received_time)
        
        # 2. Start processing
        start_time = get_document_processing_start_time()
        
        # 3. Calculate processing deadline
        deadline = get_processing_deadline(received_time, processing_sla_minutes=5)
        
        # 4. Check if processing is overdue (should not be)
        assert is_processing_overdue(received_time, processing_sla_minutes=5) is False
        
        # 5. Simulate processing delay
        with freeze_time("2023-04-15 12:32:45", tz_offset=0):
            # 6. Calculate processing time
            proc_time, formatted_proc_time = calculate_document_processing_time(start_time)
            
            # 7. Check if processing is now overdue (should not be, only 2 minutes passed)
            assert is_processing_overdue(received_time, processing_sla_minutes=5) is False
            
            # 8. Format document metadata with processing timestamp
            metadata_timestamp = format_document_metadata_timestamp()
            
            # 9. Create message with timestamp
            message = get_message_timestamp()
            
            # Assertions
            assert proc_time > 0
            assert "2 minutes" in formatted_proc_time
            assert metadata_timestamp == "2023-04-15T12:32:45+00:00"
            assert message["timestamp"] == "2023-04-15T12:32:45+00:00"

    def test_timezone_conversion_workflow(self):
        """Test a workflow involving timezone conversions."""
        # Create a datetime in UTC
        utc_time = datetime.datetime(2023, 4, 15, 12, 30, 45, tzinfo=datetime.timezone.utc)
        
        # Convert to different timezones (mocking the actual conversion)
        with patch("src.utils.time_utils.USING_ZONEINFO", True):
            with patch("src.utils.time_utils.ZoneInfo") as mock_zoneinfo:
                # Mock EST timezone (UTC-5)
                est_tz = datetime.timezone(datetime.timedelta(hours=-5))
                mock_zoneinfo.return_value = est_tz
                
                # Convert to EST
                est_time = convert_timezone(utc_time, "America/New_York")
                
                # Mock JST timezone (UTC+9)
                jst_tz = datetime.timezone(datetime.timedelta(hours=9))
                mock_zoneinfo.return_value = jst_tz
                
                # Convert to JST
                jst_time = convert_timezone(utc_time, "Asia/Tokyo")
                
                # Assertions
                assert est_time.tzinfo == est_tz
                assert jst_time.tzinfo == jst_tz
                
                # The actual hour would be different, but we're mocking the conversion
                # In a real scenario, EST would be 07:30:45 and JST would be 21:30:45


if __name__ == "__main__":
    pytest.main()