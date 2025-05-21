#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the time_utils module.

This module contains tests for timestamp generation, date comparison,
duration calculation, and time formatting functions in the time_utils module.
"""

import unittest
from unittest.mock import patch, Mock
import datetime
import time
from freezegun import freeze_time

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
    timestamp_to_unix,
    unix_to_timestamp,
    convert_timezone,
    get_timezone_offset,
    add_timezone_info,
    get_timestamp_for_filename
)


class TestTimeUtils(unittest.TestCase):
    """Test cases for time_utils module."""

    def setUp(self):
        """Set up test fixtures."""
        # Fixed test datetime (2023-04-15 14:30:45.123456 UTC)
        self.test_dt = datetime.datetime(2023, 4, 15, 14, 30, 45, 123456, tzinfo=datetime.timezone.utc)
        self.test_dt_naive = datetime.datetime(2023, 4, 15, 14, 30, 45, 123456)
        
        # Fixed ISO 8601 string representation
        self.test_iso_str = "2023-04-15T14:30:45.123456+00:00"
        
        # Fixed Unix timestamp (seconds since epoch)
        self.test_unix_timestamp = 1681568645.123456

    @freeze_time("2023-04-15 14:30:45.123456")
    def test_get_current_timestamp(self):
        """Test get_current_timestamp returns the current time with UTC timezone."""
        timestamp = get_current_timestamp()
        self.assertEqual(timestamp.year, 2023)
        self.assertEqual(timestamp.month, 4)
        self.assertEqual(timestamp.day, 15)
        self.assertEqual(timestamp.hour, 14)
        self.assertEqual(timestamp.minute, 30)
        self.assertEqual(timestamp.second, 45)
        self.assertEqual(timestamp.microsecond, 123456)
        self.assertEqual(timestamp.tzinfo, datetime.timezone.utc)

    @freeze_time("2023-04-15 14:30:45.123456")
    def test_get_timestamp_str(self):
        """Test get_timestamp_str returns the current time as an ISO 8601 string."""
        timestamp_str = get_timestamp_str()
        self.assertEqual(timestamp_str, "2023-04-15T14:30:45.123456+00:00")

    @patch('src.utils.time_utils.USING_ZONEINFO', True)
    @patch('src.utils.time_utils.ZoneInfo')
    @freeze_time("2023-04-15 14:30:45.123456")
    def test_get_timestamp_with_timezone_zoneinfo(self, mock_zoneinfo):
        """Test get_timestamp_with_timezone using ZoneInfo."""
        # Mock ZoneInfo to return a fixed timezone
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz
        
        timestamp = get_timestamp_with_timezone("America/New_York")
        
        # Verify ZoneInfo was called with the correct timezone
        mock_zoneinfo.assert_called_once_with("America/New_York")
        
        # Verify the timestamp has the correct time and timezone
        self.assertEqual(timestamp.year, 2023)
        self.assertEqual(timestamp.month, 4)
        self.assertEqual(timestamp.day, 15)
        self.assertEqual(timestamp.hour, 14)
        self.assertEqual(timestamp.minute, 30)
        self.assertEqual(timestamp.second, 45)
        self.assertEqual(timestamp.microsecond, 123456)
        self.assertEqual(timestamp.tzinfo, mock_tz)

    @patch('src.utils.time_utils.USING_ZONEINFO', False)
    @patch('src.utils.time_utils.pytz')
    @freeze_time("2023-04-15 14:30:45.123456")
    def test_get_timestamp_with_timezone_pytz(self, mock_pytz):
        """Test get_timestamp_with_timezone using pytz."""
        # Mock pytz to return a fixed timezone
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz
        
        timestamp = get_timestamp_with_timezone("America/New_York")
        
        # Verify pytz.timezone was called with the correct timezone
        mock_pytz.timezone.assert_called_once_with("America/New_York")
        
        # Verify the timestamp has the correct time and timezone
        self.assertEqual(timestamp.year, 2023)
        self.assertEqual(timestamp.month, 4)
        self.assertEqual(timestamp.day, 15)
        self.assertEqual(timestamp.hour, 14)
        self.assertEqual(timestamp.minute, 30)
        self.assertEqual(timestamp.second, 45)
        self.assertEqual(timestamp.microsecond, 123456)
        self.assertEqual(timestamp.tzinfo, mock_tz)

    def test_get_timestamp_with_timezone_invalid(self):
        """Test get_timestamp_with_timezone with an invalid timezone."""
        with self.assertRaises(ValueError):
            get_timestamp_with_timezone("Invalid/Timezone")

    def test_format_timestamp(self):
        """Test format_timestamp formats a datetime as an ISO 8601 string."""
        # Test with timezone-aware datetime
        formatted = format_timestamp(self.test_dt)
        self.assertEqual(formatted, self.test_iso_str)
        
        # Test with naive datetime (should add UTC timezone)
        formatted_naive = format_timestamp(self.test_dt_naive)
        self.assertEqual(formatted_naive, self.test_iso_str)
        
        # Test without timezone information
        formatted_no_tz = format_timestamp(self.test_dt, include_timezone=False)
        self.assertEqual(formatted_no_tz, "2023-04-15T14:30:45.123456")

    def test_parse_timestamp(self):
        """Test parse_timestamp parses an ISO 8601 string into a datetime."""
        # Test with standard ISO format
        parsed = parse_timestamp(self.test_iso_str)
        self.assertEqual(parsed, self.test_dt)
        
        # Test with 'Z' timezone designator
        parsed_z = parse_timestamp("2023-04-15T14:30:45.123456Z")
        self.assertEqual(parsed_z, self.test_dt)
        
        # Test with invalid format
        with self.assertRaises(ValueError):
            parse_timestamp("not-a-timestamp")

    def test_format_human_readable(self):
        """Test format_human_readable formats a datetime in a human-readable format."""
        formatted = format_human_readable(self.test_dt)
        self.assertEqual(formatted, "2023-04-15 14:30:45")

    def test_is_same_day(self):
        """Test is_same_day checks if two datetimes are on the same day."""
        # Same day
        dt1 = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2 = datetime.datetime(2023, 4, 15, 22, 0, 0)
        self.assertTrue(is_same_day(dt1, dt2))
        
        # Different day
        dt3 = datetime.datetime(2023, 4, 16, 10, 0, 0)
        self.assertFalse(is_same_day(dt1, dt3))

    def test_is_before(self):
        """Test is_before checks if the first datetime is before the second."""
        # dt1 is before dt2
        dt1 = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2 = datetime.datetime(2023, 4, 15, 22, 0, 0)
        self.assertTrue(is_before(dt1, dt2))
        
        # dt1 is not before dt2
        self.assertFalse(is_before(dt2, dt1))
        
        # Same datetime
        self.assertFalse(is_before(dt1, dt1))
        
        # Test with timezone-naive datetimes
        dt1_naive = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2_naive = datetime.datetime(2023, 4, 15, 22, 0, 0)
        self.assertTrue(is_before(dt1_naive, dt2_naive))

    def test_is_after(self):
        """Test is_after checks if the first datetime is after the second."""
        # dt2 is after dt1
        dt1 = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2 = datetime.datetime(2023, 4, 15, 22, 0, 0)
        self.assertTrue(is_after(dt2, dt1))
        
        # dt1 is not after dt2
        self.assertFalse(is_after(dt1, dt2))
        
        # Same datetime
        self.assertFalse(is_after(dt1, dt1))
        
        # Test with timezone-naive datetimes
        dt1_naive = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2_naive = datetime.datetime(2023, 4, 15, 22, 0, 0)
        self.assertTrue(is_after(dt2_naive, dt1_naive))

    def test_is_between(self):
        """Test is_between checks if a datetime is between two others."""
        # dt2 is between dt1 and dt3
        dt1 = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2 = datetime.datetime(2023, 4, 15, 14, 0, 0)
        dt3 = datetime.datetime(2023, 4, 15, 22, 0, 0)
        self.assertTrue(is_between(dt2, dt1, dt3))
        
        # dt1 is not between dt2 and dt3
        self.assertFalse(is_between(dt1, dt2, dt3))
        
        # Inclusive bounds
        self.assertTrue(is_between(dt1, dt1, dt3))
        self.assertTrue(is_between(dt3, dt1, dt3))
        
        # Test with timezone-naive datetimes
        dt1_naive = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2_naive = datetime.datetime(2023, 4, 15, 14, 0, 0)
        dt3_naive = datetime.datetime(2023, 4, 15, 22, 0, 0)
        self.assertTrue(is_between(dt2_naive, dt1_naive, dt3_naive))

    def test_calculate_duration(self):
        """Test calculate_duration calculates the duration between two datetimes."""
        # 12 hours difference
        dt1 = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2 = datetime.datetime(2023, 4, 15, 22, 0, 0)
        duration = calculate_duration(dt1, dt2)
        self.assertEqual(duration, datetime.timedelta(hours=12))
        
        # Negative duration (dt2 before dt1)
        duration_neg = calculate_duration(dt2, dt1)
        self.assertEqual(duration_neg, datetime.timedelta(hours=-12))
        
        # Test with timezone-naive datetimes
        dt1_naive = datetime.datetime(2023, 4, 15, 10, 0, 0)
        dt2_naive = datetime.datetime(2023, 4, 15, 22, 0, 0)
        duration_naive = calculate_duration(dt1_naive, dt2_naive)
        self.assertEqual(duration_naive, datetime.timedelta(hours=12))

    def test_format_duration(self):
        """Test format_duration formats a timedelta in a human-readable format."""
        # Test with days, hours, minutes, seconds
        td = datetime.timedelta(days=2, hours=3, minutes=45, seconds=30)
        formatted = format_duration(td)
        self.assertEqual(formatted, "2 days, 3 hours, 45 minutes, 30.00 seconds")
        
        # Test with only hours
        td_hours = datetime.timedelta(hours=5)
        formatted_hours = format_duration(td_hours)
        self.assertEqual(formatted_hours, "5 hours")
        
        # Test with only minutes
        td_minutes = datetime.timedelta(minutes=10)
        formatted_minutes = format_duration(td_minutes)
        self.assertEqual(formatted_minutes, "10 minutes")
        
        # Test with only seconds
        td_seconds = datetime.timedelta(seconds=15)
        formatted_seconds = format_duration(td_seconds)
        self.assertEqual(formatted_seconds, "15.00 seconds")
        
        # Test with zero duration
        td_zero = datetime.timedelta(0)
        formatted_zero = format_duration(td_zero)
        self.assertEqual(formatted_zero, "0.00 seconds")

    def test_format_duration_short(self):
        """Test format_duration_short formats a timedelta in a short format."""
        # Test with days, hours, minutes, seconds
        td = datetime.timedelta(days=2, hours=3, minutes=45, seconds=30)
        formatted = format_duration_short(td)
        self.assertEqual(formatted, "2d 3h 45m 30s")
        
        # Test with only hours
        td_hours = datetime.timedelta(hours=5)
        formatted_hours = format_duration_short(td_hours)
        self.assertEqual(formatted_hours, "5h")
        
        # Test with only minutes
        td_minutes = datetime.timedelta(minutes=10)
        formatted_minutes = format_duration_short(td_minutes)
        self.assertEqual(formatted_minutes, "10m")
        
        # Test with only seconds
        td_seconds = datetime.timedelta(seconds=15)
        formatted_seconds = format_duration_short(td_seconds)
        self.assertEqual(formatted_seconds, "15s")
        
        # Test with zero duration
        td_zero = datetime.timedelta(0)
        formatted_zero = format_duration_short(td_zero)
        self.assertEqual(formatted_zero, "0s")

    @freeze_time("2023-04-15 14:30:45.123456")
    def test_calculate_age(self):
        """Test calculate_age calculates the age of a datetime."""
        # 1 day old
        dt = datetime.datetime(2023, 4, 14, 14, 30, 45, 123456, tzinfo=datetime.timezone.utc)
        age = calculate_age(dt)
        self.assertEqual(age, datetime.timedelta(days=1))
        
        # Test with timezone-naive datetime
        dt_naive = datetime.datetime(2023, 4, 14, 14, 30, 45, 123456)
        age_naive = calculate_age(dt_naive)
        self.assertEqual(age_naive, datetime.timedelta(days=1))

    @freeze_time("2023-04-15 14:30:45.123456")
    def test_format_age(self):
        """Test format_age formats the age of a datetime."""
        # 1 day old
        dt = datetime.datetime(2023, 4, 14, 14, 30, 45, 123456, tzinfo=datetime.timezone.utc)
        
        # Test with default format
        formatted = format_age(dt)
        self.assertEqual(formatted, "1 day")
        
        # Test with short format
        formatted_short = format_age(dt, short=True)
        self.assertEqual(formatted_short, "1d")

    def test_calculate_processing_time(self):
        """Test calculate_processing_time calculates processing time from a start time."""
        with patch('time.time') as mock_time:
            # Mock time.time() to return a fixed value
            mock_time.return_value = 100.5
            
            # Test with start time 100.0 (0.5 seconds elapsed)
            processing_time = calculate_processing_time(100.0)
            self.assertEqual(processing_time, 0.5)

    def test_format_processing_time(self):
        """Test format_processing_time formats processing time in a human-readable format."""
        # Test with seconds
        formatted_seconds = format_processing_time(5.25)
        self.assertEqual(formatted_seconds, "5.25 s")
        
        # Test with milliseconds
        formatted_ms = format_processing_time(0.25)
        self.assertEqual(formatted_ms, "250.00 ms")
        
        # Test with microseconds
        formatted_us = format_processing_time(0.0005)
        self.assertEqual(formatted_us, "500.00 μs")

    def test_get_document_processing_start_time(self):
        """Test get_document_processing_start_time returns the current time."""
        with patch('time.time') as mock_time:
            # Mock time.time() to return a fixed value
            mock_time.return_value = 100.0
            
            start_time = get_document_processing_start_time()
            self.assertEqual(start_time, 100.0)

    def test_calculate_document_processing_time(self):
        """Test calculate_document_processing_time calculates and formats processing time."""
        with patch('time.time') as mock_time:
            # Mock time.time() to return a fixed value
            mock_time.return_value = 100.5
            
            # Test with start time 100.0 (0.5 seconds elapsed)
            proc_time, formatted_time = calculate_document_processing_time(100.0)
            self.assertEqual(proc_time, 0.5)
            self.assertEqual(formatted_time, "0.50 s")

    def test_format_timestamp_for_message(self):
        """Test format_timestamp_for_message formats a timestamp for message payloads."""
        # Test with provided datetime
        formatted = format_timestamp_for_message(self.test_dt)
        self.assertEqual(formatted, self.test_iso_str)
        
        # Test with naive datetime
        formatted_naive = format_timestamp_for_message(self.test_dt_naive)
        self.assertEqual(formatted_naive, self.test_iso_str)
        
        # Test with current time
        with patch('src.utils.time_utils.get_current_timestamp') as mock_get_current:
            mock_get_current.return_value = self.test_dt
            formatted_current = format_timestamp_for_message()
            self.assertEqual(formatted_current, self.test_iso_str)

    def test_format_document_metadata_timestamp(self):
        """Test format_document_metadata_timestamp formats a timestamp for document metadata."""
        # This function calls format_timestamp_for_message, so we can test by verifying the call
        with patch('src.utils.time_utils.format_timestamp_for_message') as mock_format:
            mock_format.return_value = self.test_iso_str
            
            # Test with provided datetime
            formatted = format_document_metadata_timestamp(self.test_dt)
            mock_format.assert_called_once_with(self.test_dt)
            self.assertEqual(formatted, self.test_iso_str)

    def test_format_log_timestamp(self):
        """Test format_log_timestamp formats a timestamp for log entries."""
        # Test with provided datetime
        formatted = format_log_timestamp(self.test_dt)
        self.assertEqual(formatted, "2023-04-15T14:30:45.123456Z")
        
        # Test with naive datetime
        formatted_naive = format_log_timestamp(self.test_dt_naive)
        self.assertEqual(formatted_naive, "2023-04-15T14:30:45.123456Z")
        
        # Test with current time
        with patch('src.utils.time_utils.get_current_timestamp') as mock_get_current:
            mock_get_current.return_value = self.test_dt
            formatted_current = format_log_timestamp()
            self.assertEqual(formatted_current, "2023-04-15T14:30:45.123456Z")

    def test_compare_document_timestamps(self):
        """Test compare_document_timestamps compares two document timestamps."""
        # dt1 is before dt2
        dt1 = datetime.datetime(2023, 4, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        dt2 = datetime.datetime(2023, 4, 15, 22, 0, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(compare_document_timestamps(dt1, dt2), -1)
        
        # dt2 is after dt1
        self.assertEqual(compare_document_timestamps(dt2, dt1), 1)
        
        # Same datetime
        self.assertEqual(compare_document_timestamps(dt1, dt1), 0)
        
        # Test with string timestamps
        dt1_str = "2023-04-15T10:00:00+00:00"
        dt2_str = "2023-04-15T22:00:00+00:00"
        self.assertEqual(compare_document_timestamps(dt1_str, dt2_str), -1)
        
        # Test with mixed types
        self.assertEqual(compare_document_timestamps(dt1, dt2_str), -1)
        self.assertEqual(compare_document_timestamps(dt1_str, dt2), -1)

    @freeze_time("2023-04-15 14:30:45.123456")
    def test_get_message_timestamp(self):
        """Test get_message_timestamp returns a timestamp dictionary for message payloads."""
        timestamp_dict = get_message_timestamp()
        
        self.assertIn("timestamp", timestamp_dict)
        self.assertIn("unix_timestamp", timestamp_dict)
        self.assertIn("timezone", timestamp_dict)
        
        self.assertEqual(timestamp_dict["timestamp"], "2023-04-15T14:30:45.123456+00:00")
        self.assertAlmostEqual(timestamp_dict["unix_timestamp"], 1681568645.123456, places=3)
        self.assertEqual(timestamp_dict["timezone"], "UTC")

    def test_validate_timestamp_format(self):
        """Test validate_timestamp_format validates ISO 8601 timestamp strings."""
        # Valid formats
        self.assertTrue(validate_timestamp_format("2023-04-15T14:30:45+00:00"))
        self.assertTrue(validate_timestamp_format("2023-04-15T14:30:45Z"))
        self.assertTrue(validate_timestamp_format("2023-04-15T14:30:45.123456+00:00"))
        
        # Invalid formats
        self.assertFalse(validate_timestamp_format("2023-04-15"))
        self.assertFalse(validate_timestamp_format("14:30:45"))
        self.assertFalse(validate_timestamp_format("not-a-timestamp"))

    def test_get_document_age_category(self):
        """Test get_document_age_category categorizes documents based on age."""
        with freeze_time("2023-04-15 14:30:45.123456"):
            # New (less than 1 day old)
            dt_new = datetime.datetime(2023, 4, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
            self.assertEqual(get_document_age_category(dt_new), "new")
            
            # Recent (less than 1 week old)
            dt_recent = datetime.datetime(2023, 4, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)
            self.assertEqual(get_document_age_category(dt_recent), "recent")
            
            # Old (less than 1 month old)
            dt_old = datetime.datetime(2023, 3, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
            self.assertEqual(get_document_age_category(dt_old), "old")
            
            # Archived (1 month or older)
            dt_archived = datetime.datetime(2023, 3, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
            self.assertEqual(get_document_age_category(dt_archived), "archived")
            
            # Test with string timestamp
            dt_new_str = "2023-04-15T10:00:00+00:00"
            self.assertEqual(get_document_age_category(dt_new_str), "new")

    def test_get_processing_deadline(self):
        """Test get_processing_deadline calculates the processing deadline based on SLA."""
        # Test with default SLA (5 minutes)
        received = datetime.datetime(2023, 4, 15, 14, 30, 0, tzinfo=datetime.timezone.utc)
        deadline = get_processing_deadline(received)
        expected = datetime.datetime(2023, 4, 15, 14, 35, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(deadline, expected)
        
        # Test with custom SLA (10 minutes)
        deadline_custom = get_processing_deadline(received, processing_sla_minutes=10)
        expected_custom = datetime.datetime(2023, 4, 15, 14, 40, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(deadline_custom, expected_custom)
        
        # Test with string timestamp
        received_str = "2023-04-15T14:30:00+00:00"
        deadline_str = get_processing_deadline(received_str)
        self.assertEqual(deadline_str, expected)

    def test_is_processing_overdue(self):
        """Test is_processing_overdue checks if processing is overdue based on SLA."""
        with freeze_time("2023-04-15 14:36:00"):
            # Overdue (received 7 minutes ago, SLA is 5 minutes)
            received_overdue = datetime.datetime(2023, 4, 15, 14, 29, 0, tzinfo=datetime.timezone.utc)
            self.assertTrue(is_processing_overdue(received_overdue))
            
            # Not overdue (received 3 minutes ago, SLA is 5 minutes)
            received_not_overdue = datetime.datetime(2023, 4, 15, 14, 33, 0, tzinfo=datetime.timezone.utc)
            self.assertFalse(is_processing_overdue(received_not_overdue))
            
            # Test with custom SLA (10 minutes)
            self.assertFalse(is_processing_overdue(received_overdue, processing_sla_minutes=10))
            
            # Test with string timestamp
            received_overdue_str = "2023-04-15T14:29:00+00:00"
            self.assertTrue(is_processing_overdue(received_overdue_str))

    def test_format_time_remaining(self):
        """Test format_time_remaining formats the time remaining until a deadline."""
        with freeze_time("2023-04-15 14:30:00"):
            # 5 minutes remaining
            deadline = datetime.datetime(2023, 4, 15, 14, 35, 0, tzinfo=datetime.timezone.utc)
            formatted = format_time_remaining(deadline)
            self.assertEqual(formatted, "5 minutes")
            
            # Overdue
            deadline_overdue = datetime.datetime(2023, 4, 15, 14, 25, 0, tzinfo=datetime.timezone.utc)
            formatted_overdue = format_time_remaining(deadline_overdue)
            self.assertEqual(formatted_overdue, "Overdue")
            
            # Test with naive datetime
            deadline_naive = datetime.datetime(2023, 4, 15, 14, 35, 0)
            formatted_naive = format_time_remaining(deadline_naive)
            self.assertEqual(formatted_naive, "5 minutes")

    def test_timestamp_to_unix(self):
        """Test timestamp_to_unix converts a datetime to a Unix timestamp."""
        # Test with timezone-aware datetime
        unix_timestamp = timestamp_to_unix(self.test_dt)
        self.assertAlmostEqual(unix_timestamp, self.test_unix_timestamp, places=3)
        
        # Test with naive datetime
        unix_timestamp_naive = timestamp_to_unix(self.test_dt_naive)
        self.assertAlmostEqual(unix_timestamp_naive, self.test_unix_timestamp, places=3)

    def test_unix_to_timestamp(self):
        """Test unix_to_timestamp converts a Unix timestamp to a datetime."""
        dt = unix_to_timestamp(self.test_unix_timestamp)
        
        # Check that the datetime is correct (allowing for small floating-point differences)
        self.assertEqual(dt.year, self.test_dt.year)
        self.assertEqual(dt.month, self.test_dt.month)
        self.assertEqual(dt.day, self.test_dt.day)
        self.assertEqual(dt.hour, self.test_dt.hour)
        self.assertEqual(dt.minute, self.test_dt.minute)
        self.assertEqual(dt.second, self.test_dt.second)
        self.assertEqual(dt.tzinfo, datetime.timezone.utc)

    @patch('src.utils.time_utils.USING_ZONEINFO', True)
    @patch('src.utils.time_utils.ZoneInfo')
    def test_convert_timezone_zoneinfo(self, mock_zoneinfo):
        """Test convert_timezone using ZoneInfo."""
        # Mock ZoneInfo to return a fixed timezone
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz
        
        # Create a datetime with UTC timezone
        dt = datetime.datetime(2023, 4, 15, 14, 30, 45, tzinfo=datetime.timezone.utc)
        
        # Mock the astimezone method
        expected_result = datetime.datetime(2023, 4, 15, 10, 30, 45, tzinfo=mock_tz)
        dt.astimezone = Mock(return_value=expected_result)
        
        # Convert to America/New_York
        result = convert_timezone(dt, "America/New_York")
        
        # Verify ZoneInfo was called with the correct timezone
        mock_zoneinfo.assert_called_once_with("America/New_York")
        
        # Verify astimezone was called with the correct timezone
        dt.astimezone.assert_called_once_with(mock_tz)
        
        # Verify the result
        self.assertEqual(result, expected_result)

    @patch('src.utils.time_utils.USING_ZONEINFO', False)
    @patch('src.utils.time_utils.pytz')
    def test_convert_timezone_pytz(self, mock_pytz):
        """Test convert_timezone using pytz."""
        # Mock pytz to return a fixed timezone
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz
        
        # Create a datetime with UTC timezone
        dt = datetime.datetime(2023, 4, 15, 14, 30, 45, tzinfo=datetime.timezone.utc)
        
        # Mock the astimezone method
        expected_result = datetime.datetime(2023, 4, 15, 10, 30, 45, tzinfo=mock_tz)
        dt.astimezone = Mock(return_value=expected_result)
        
        # Convert to America/New_York
        result = convert_timezone(dt, "America/New_York")
        
        # Verify pytz.timezone was called with the correct timezone
        mock_pytz.timezone.assert_called_once_with("America/New_York")
        
        # Verify astimezone was called with the correct timezone
        dt.astimezone.assert_called_once_with(mock_tz)
        
        # Verify the result
        self.assertEqual(result, expected_result)

    def test_convert_timezone_invalid(self):
        """Test convert_timezone with an invalid timezone."""
        dt = datetime.datetime(2023, 4, 15, 14, 30, 45, tzinfo=datetime.timezone.utc)
        with self.assertRaises(ValueError):
            convert_timezone(dt, "Invalid/Timezone")

    @patch('src.utils.time_utils.USING_ZONEINFO', True)
    @patch('src.utils.time_utils.ZoneInfo')
    @freeze_time("2023-04-15 14:30:45.123456")
    def test_get_timezone_offset_zoneinfo(self, mock_zoneinfo):
        """Test get_timezone_offset using ZoneInfo."""
        # Mock ZoneInfo to return a fixed timezone
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz
        
        # Mock datetime.astimezone to return a datetime with a fixed offset
        mock_dt = Mock()
        mock_dt.strftime.return_value = "-0400"
        
        with patch('datetime.datetime.astimezone', return_value=mock_dt):
            # Get offset for America/New_York
            offset = get_timezone_offset("America/New_York")
            
            # Verify ZoneInfo was called with the correct timezone
            mock_zoneinfo.assert_called_once_with("America/New_York")
            
            # Verify the offset
            self.assertEqual(offset, "-04:00")

    @patch('src.utils.time_utils.USING_ZONEINFO', False)
    @patch('src.utils.time_utils.pytz')
    @freeze_time("2023-04-15 14:30:45.123456")
    def test_get_timezone_offset_pytz(self, mock_pytz):
        """Test get_timezone_offset using pytz."""
        # Mock pytz to return a fixed timezone
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz
        
        # Mock datetime.astimezone to return a datetime with a fixed offset
        mock_dt = Mock()
        mock_dt.strftime.return_value = "-0400"
        
        with patch('datetime.datetime.astimezone', return_value=mock_dt):
            # Get offset for America/New_York
            offset = get_timezone_offset("America/New_York")
            
            # Verify pytz.timezone was called with the correct timezone
            mock_pytz.timezone.assert_called_once_with("America/New_York")
            
            # Verify the offset
            self.assertEqual(offset, "-04:00")

    def test_get_timezone_offset_invalid(self):
        """Test get_timezone_offset with an invalid timezone."""
        with self.assertRaises(ValueError):
            get_timezone_offset("Invalid/Timezone")

    @patch('src.utils.time_utils.USING_ZONEINFO', True)
    @patch('src.utils.time_utils.ZoneInfo')
    def test_add_timezone_info_zoneinfo(self, mock_zoneinfo):
        """Test add_timezone_info using ZoneInfo."""
        # Mock ZoneInfo to return a fixed timezone
        mock_tz = Mock()
        mock_zoneinfo.return_value = mock_tz
        
        # Create a naive datetime
        dt = datetime.datetime(2023, 4, 15, 14, 30, 45)
        
        # Add timezone info
        result = add_timezone_info(dt, "America/New_York")
        
        # Verify ZoneInfo was called with the correct timezone
        mock_zoneinfo.assert_called_once_with("America/New_York")
        
        # Verify the result has the correct timezone
        self.assertEqual(result.tzinfo, mock_tz)

    @patch('src.utils.time_utils.USING_ZONEINFO', False)
    @patch('src.utils.time_utils.pytz')
    def test_add_timezone_info_pytz(self, mock_pytz):
        """Test add_timezone_info using pytz."""
        # Mock pytz to return a fixed timezone
        mock_tz = Mock()
        mock_pytz.timezone.return_value = mock_tz
        
        # Create a naive datetime
        dt = datetime.datetime(2023, 4, 15, 14, 30, 45)
        
        # Mock the localize method
        expected_result = datetime.datetime(2023, 4, 15, 14, 30, 45, tzinfo=mock_tz)
        mock_tz.localize = Mock(return_value=expected_result)
        
        # Add timezone info
        result = add_timezone_info(dt, "America/New_York")
        
        # Verify pytz.timezone was called with the correct timezone
        mock_pytz.timezone.assert_called_once_with("America/New_York")
        
        # Verify localize was called with the correct datetime
        mock_tz.localize.assert_called_once_with(dt)
        
        # Verify the result
        self.assertEqual(result, expected_result)

    def test_add_timezone_info_already_aware(self):
        """Test add_timezone_info with a datetime that already has timezone info."""
        dt = datetime.datetime(2023, 4, 15, 14, 30, 45, tzinfo=datetime.timezone.utc)
        with self.assertRaises(ValueError):
            add_timezone_info(dt, "America/New_York")

    def test_add_timezone_info_invalid(self):
        """Test add_timezone_info with an invalid timezone."""
        dt = datetime.datetime(2023, 4, 15, 14, 30, 45)
        with self.assertRaises(ValueError):
            add_timezone_info(dt, "Invalid/Timezone")

    def test_get_timestamp_for_filename(self):
        """Test get_timestamp_for_filename returns a timestamp suitable for filenames."""
        with freeze_time("2023-04-15 14:30:45"):
            timestamp = get_timestamp_for_filename()
            self.assertEqual(timestamp, "20230415_143045")


if __name__ == "__main__":
    unittest.main()