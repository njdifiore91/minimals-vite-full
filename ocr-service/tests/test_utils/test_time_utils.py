#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the time_utils module.

This module contains tests for timestamp generation, date comparison, duration calculation,
and time formatting functions to ensure consistent timestamp handling in logs, message
publishing, and document metadata.
"""

import datetime
import time
import re
import pytest
import pytz
from freezegun import freeze_time
from dateutil import parser

from ocr_service.utils.time_utils import (
    is_valid_date,
    get_current_timestamp,
    format_datetime,
    format_date,
    format_time,
    format_timestamp,
    format_time_to_now,
    is_date_between,
    is_date_after,
    is_same_date,
    get_date_range_label,
    add_time,
    subtract_time,
    parse_iso_datetime,
    calculate_processing_time,
    calculate_document_age,
    get_processing_timestamp,
    get_log_timestamp,
    get_expiry_timestamp,
    DEFAULT_TIMEZONE,
    FORMAT_PATTERNS
)


class TestIsValidDate:
    """Tests for the is_valid_date function."""

    def test_valid_datetime(self):
        """Test is_valid_date with a valid datetime object."""
        dt = datetime.datetime.now()
        assert is_valid_date(dt) is True

    def test_valid_date(self):
        """Test is_valid_date with a valid date object."""
        d = datetime.date.today()
        assert is_valid_date(d) is True

    def test_valid_iso_string(self):
        """Test is_valid_date with a valid ISO 8601 string."""
        dt_str = "2023-01-15T12:30:45Z"
        assert is_valid_date(dt_str) is True

    def test_valid_timestamp_int(self):
        """Test is_valid_date with a valid integer timestamp."""
        ts = int(time.time())
        assert is_valid_date(ts) is True

    def test_valid_timestamp_float(self):
        """Test is_valid_date with a valid float timestamp."""
        ts = time.time()
        assert is_valid_date(ts) is True

    def test_none_value(self):
        """Test is_valid_date with None value."""
        assert is_valid_date(None) is False

    def test_invalid_string(self):
        """Test is_valid_date with an invalid string."""
        assert is_valid_date("not a date") is False

    def test_invalid_type(self):
        """Test is_valid_date with an invalid type."""
        assert is_valid_date([]) is False
        assert is_valid_date({}) is False

    def test_overflow_timestamp(self):
        """Test is_valid_date with an overflow timestamp."""
        # A timestamp too large for datetime conversion
        assert is_valid_date(10**20) is False


class TestGetCurrentTimestamp:
    """Tests for the get_current_timestamp function."""

    @freeze_time("2023-05-15 12:30:45")
    def test_get_current_timestamp_default_timezone(self):
        """Test get_current_timestamp with default timezone (UTC)."""
        timestamp = get_current_timestamp()
        assert timestamp == "2023-05-15T12:30:45.000Z"

    @freeze_time("2023-05-15 12:30:45")
    def test_get_current_timestamp_custom_timezone(self):
        """Test get_current_timestamp with a custom timezone."""
        est = pytz.timezone('US/Eastern')
        timestamp = get_current_timestamp(est)
        # EST is UTC-5 (or UTC-4 during daylight saving)
        # Since freeze_time sets the UTC time, the EST time would be 5 hours behind
        # But the function converts the current time to the specified timezone
        assert timestamp == "2023-05-15T08:30:45.000Z"

    def test_get_current_timestamp_format(self):
        """Test that get_current_timestamp returns a properly formatted ISO 8601 string."""
        timestamp = get_current_timestamp()
        # ISO 8601 format: YYYY-MM-DDThh:mm:ss.sssZ
        pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$'
        assert re.match(pattern, timestamp) is not None


class TestFormatFunctions:
    """Tests for the format_datetime, format_date, format_time, and format_timestamp functions."""

    @freeze_time("2023-05-15 12:30:45")
    def test_format_datetime_default_template(self):
        """Test format_datetime with default template."""
        dt = datetime.datetime.now()
        formatted = format_datetime(dt)
        assert formatted == "15 May 2023 12:30 PM"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_datetime_custom_template(self):
        """Test format_datetime with a custom template."""
        dt = datetime.datetime.now()
        formatted = format_datetime(dt, "%Y-%m-%d %H:%M:%S")
        assert formatted == "2023-05-15 12:30:45"

    def test_format_datetime_invalid_date(self):
        """Test format_datetime with an invalid date."""
        formatted = format_datetime(None)
        assert formatted == "Invalid date"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_date_default_template(self):
        """Test format_date with default template."""
        dt = datetime.datetime.now()
        formatted = format_date(dt)
        assert formatted == "15 May 2023"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_date_custom_template(self):
        """Test format_date with a custom template."""
        dt = datetime.datetime.now()
        formatted = format_date(dt, "%Y-%m-%d")
        assert formatted == "2023-05-15"

    def test_format_date_invalid_date(self):
        """Test format_date with an invalid date."""
        formatted = format_date(None)
        assert formatted == "Invalid date"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_default_template(self):
        """Test format_time with default template."""
        dt = datetime.datetime.now()
        formatted = format_time(dt)
        assert formatted == "12:30 PM"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_custom_template(self):
        """Test format_time with a custom template."""
        dt = datetime.datetime.now()
        formatted = format_time(dt, "%H:%M:%S")
        assert formatted == "12:30:45"

    def test_format_time_invalid_date(self):
        """Test format_time with an invalid date."""
        formatted = format_time(None)
        assert formatted == "Invalid date"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_timestamp(self):
        """Test format_timestamp with a valid datetime."""
        dt = datetime.datetime.now()
        timestamp = format_timestamp(dt)
        # Get the expected timestamp
        expected = int(dt.timestamp())
        assert timestamp == expected

    def test_format_timestamp_invalid_date(self):
        """Test format_timestamp with an invalid date."""
        timestamp = format_timestamp(None)
        assert timestamp == "Invalid date"


class TestFormatTimeToNow:
    """Tests for the format_time_to_now function."""

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_seconds(self):
        """Test format_time_to_now with a time difference of seconds."""
        dt = datetime.datetime.now() - datetime.timedelta(seconds=30)
        result = format_time_to_now(dt)
        assert result == "a few seconds"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_minutes(self):
        """Test format_time_to_now with a time difference of minutes."""
        dt = datetime.datetime.now() - datetime.timedelta(minutes=5)
        result = format_time_to_now(dt)
        assert result == "5 minutes"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_single_minute(self):
        """Test format_time_to_now with a time difference of 1 minute."""
        dt = datetime.datetime.now() - datetime.timedelta(minutes=1)
        result = format_time_to_now(dt)
        assert result == "1 minute"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_hours(self):
        """Test format_time_to_now with a time difference of hours."""
        dt = datetime.datetime.now() - datetime.timedelta(hours=3)
        result = format_time_to_now(dt)
        assert result == "3 hours"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_single_hour(self):
        """Test format_time_to_now with a time difference of 1 hour."""
        dt = datetime.datetime.now() - datetime.timedelta(hours=1)
        result = format_time_to_now(dt)
        assert result == "1 hour"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_days(self):
        """Test format_time_to_now with a time difference of days."""
        dt = datetime.datetime.now() - datetime.timedelta(days=4)
        result = format_time_to_now(dt)
        assert result == "4 days"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_single_day(self):
        """Test format_time_to_now with a time difference of 1 day."""
        dt = datetime.datetime.now() - datetime.timedelta(days=1)
        result = format_time_to_now(dt)
        assert result == "1 day"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_weeks(self):
        """Test format_time_to_now with a time difference of weeks."""
        dt = datetime.datetime.now() - datetime.timedelta(days=14)
        result = format_time_to_now(dt)
        assert result == "2 weeks"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_single_week(self):
        """Test format_time_to_now with a time difference of 1 week."""
        dt = datetime.datetime.now() - datetime.timedelta(days=7)
        result = format_time_to_now(dt)
        assert result == "1 week"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_months(self):
        """Test format_time_to_now with a time difference of months."""
        # Approximately 2 months (60 days)
        dt = datetime.datetime.now() - datetime.timedelta(days=60)
        result = format_time_to_now(dt)
        assert result == "2 months"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_single_month(self):
        """Test format_time_to_now with a time difference of 1 month."""
        # Approximately 1 month (30 days)
        dt = datetime.datetime.now() - datetime.timedelta(days=30)
        result = format_time_to_now(dt)
        assert result == "1 month"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_years(self):
        """Test format_time_to_now with a time difference of years."""
        # Approximately 2 years (730 days)
        dt = datetime.datetime.now() - datetime.timedelta(days=730)
        result = format_time_to_now(dt)
        assert result == "2 years"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_single_year(self):
        """Test format_time_to_now with a time difference of 1 year."""
        # Approximately 1 year (365 days)
        dt = datetime.datetime.now() - datetime.timedelta(days=365)
        result = format_time_to_now(dt)
        assert result == "1 year"

    def test_format_time_to_now_invalid_date(self):
        """Test format_time_to_now with an invalid date."""
        result = format_time_to_now(None)
        assert result == "Invalid date"

    @freeze_time("2023-05-15 12:30:45")
    def test_format_time_to_now_timezone_aware(self):
        """Test format_time_to_now with timezone-aware datetimes."""
        now = datetime.datetime.now(pytz.UTC)
        dt = now - datetime.timedelta(hours=2)
        result = format_time_to_now(dt)
        assert result == "2 hours"


class TestDateComparisonFunctions:
    """Tests for the is_date_between, is_date_after, and is_same_date functions."""

    def test_is_date_between_true(self):
        """Test is_date_between when the date is between start and end dates."""
        start = datetime.datetime(2023, 1, 1)
        end = datetime.datetime(2023, 12, 31)
        input_date = datetime.datetime(2023, 6, 15)
        assert is_date_between(input_date, start, end) is True

    def test_is_date_between_false(self):
        """Test is_date_between when the date is not between start and end dates."""
        start = datetime.datetime(2023, 1, 1)
        end = datetime.datetime(2023, 12, 31)
        input_date = datetime.datetime(2024, 1, 1)
        assert is_date_between(input_date, start, end) is False

    def test_is_date_between_equal_to_start(self):
        """Test is_date_between when the date is equal to the start date."""
        start = datetime.datetime(2023, 1, 1)
        end = datetime.datetime(2023, 12, 31)
        input_date = datetime.datetime(2023, 1, 1)
        assert is_date_between(input_date, start, end) is True

    def test_is_date_between_equal_to_end(self):
        """Test is_date_between when the date is equal to the end date."""
        start = datetime.datetime(2023, 1, 1)
        end = datetime.datetime(2023, 12, 31)
        input_date = datetime.datetime(2023, 12, 31)
        assert is_date_between(input_date, start, end) is True

    def test_is_date_between_invalid_dates(self):
        """Test is_date_between with invalid dates."""
        assert is_date_between(None, "2023-01-01", "2023-12-31") is False
        assert is_date_between("2023-06-15", None, "2023-12-31") is False
        assert is_date_between("2023-06-15", "2023-01-01", None) is False

    def test_is_date_after_true(self):
        """Test is_date_after when the start date is after the end date."""
        start = datetime.datetime(2023, 6, 15)
        end = datetime.datetime(2023, 1, 1)
        assert is_date_after(start, end) is True

    def test_is_date_after_false(self):
        """Test is_date_after when the start date is not after the end date."""
        start = datetime.datetime(2023, 1, 1)
        end = datetime.datetime(2023, 6, 15)
        assert is_date_after(start, end) is False

    def test_is_date_after_equal(self):
        """Test is_date_after when the start date is equal to the end date."""
        date = datetime.datetime(2023, 1, 1)
        assert is_date_after(date, date) is False

    def test_is_date_after_invalid_dates(self):
        """Test is_date_after with invalid dates."""
        assert is_date_after(None, "2023-01-01") is False
        assert is_date_after("2023-06-15", None) is False

    def test_is_same_date_year_true(self):
        """Test is_same_date with unit_to_compare='year' when years are the same."""
        date1 = datetime.datetime(2023, 6, 15)
        date2 = datetime.datetime(2023, 1, 1)
        assert is_same_date(date1, date2, "year") is True

    def test_is_same_date_year_false(self):
        """Test is_same_date with unit_to_compare='year' when years are different."""
        date1 = datetime.datetime(2023, 6, 15)
        date2 = datetime.datetime(2022, 6, 15)
        assert is_same_date(date1, date2, "year") is False

    def test_is_same_date_month_true(self):
        """Test is_same_date with unit_to_compare='month' when months are the same."""
        date1 = datetime.datetime(2023, 6, 15)
        date2 = datetime.datetime(2023, 6, 1)
        assert is_same_date(date1, date2, "month") is True

    def test_is_same_date_month_false(self):
        """Test is_same_date with unit_to_compare='month' when months are different."""
        date1 = datetime.datetime(2023, 6, 15)
        date2 = datetime.datetime(2023, 7, 15)
        assert is_same_date(date1, date2, "month") is False

    def test_is_same_date_day_true(self):
        """Test is_same_date with unit_to_compare='day' when days are the same."""
        date1 = datetime.datetime(2023, 6, 15, 12, 0)
        date2 = datetime.datetime(2023, 6, 15, 18, 0)
        assert is_same_date(date1, date2, "day") is True

    def test_is_same_date_day_false(self):
        """Test is_same_date with unit_to_compare='day' when days are different."""
        date1 = datetime.datetime(2023, 6, 15)
        date2 = datetime.datetime(2023, 6, 16)
        assert is_same_date(date1, date2, "day") is False

    def test_is_same_date_hour_true(self):
        """Test is_same_date with unit_to_compare='hour' when hours are the same."""
        date1 = datetime.datetime(2023, 6, 15, 12, 30)
        date2 = datetime.datetime(2023, 6, 15, 12, 45)
        assert is_same_date(date1, date2, "hour") is True

    def test_is_same_date_hour_false(self):
        """Test is_same_date with unit_to_compare='hour' when hours are different."""
        date1 = datetime.datetime(2023, 6, 15, 12, 30)
        date2 = datetime.datetime(2023, 6, 15, 13, 30)
        assert is_same_date(date1, date2, "hour") is False

    def test_is_same_date_minute_true(self):
        """Test is_same_date with unit_to_compare='minute' when minutes are the same."""
        date1 = datetime.datetime(2023, 6, 15, 12, 30, 15)
        date2 = datetime.datetime(2023, 6, 15, 12, 30, 45)
        assert is_same_date(date1, date2, "minute") is True

    def test_is_same_date_minute_false(self):
        """Test is_same_date with unit_to_compare='minute' when minutes are different."""
        date1 = datetime.datetime(2023, 6, 15, 12, 30)
        date2 = datetime.datetime(2023, 6, 15, 12, 31)
        assert is_same_date(date1, date2, "minute") is False

    def test_is_same_date_second_true(self):
        """Test is_same_date with unit_to_compare='second' when seconds are the same."""
        date1 = datetime.datetime(2023, 6, 15, 12, 30, 45, 123000)
        date2 = datetime.datetime(2023, 6, 15, 12, 30, 45, 456000)
        assert is_same_date(date1, date2, "second") is True

    def test_is_same_date_second_false(self):
        """Test is_same_date with unit_to_compare='second' when seconds are different."""
        date1 = datetime.datetime(2023, 6, 15, 12, 30, 45)
        date2 = datetime.datetime(2023, 6, 15, 12, 30, 46)
        assert is_same_date(date1, date2, "second") is False

    def test_is_same_date_invalid_unit(self):
        """Test is_same_date with an invalid unit_to_compare."""
        date1 = datetime.datetime(2023, 6, 15)
        date2 = datetime.datetime(2023, 6, 15)
        assert is_same_date(date1, date2, "invalid_unit") is False

    def test_is_same_date_invalid_dates(self):
        """Test is_same_date with invalid dates."""
        assert is_same_date(None, "2023-01-01") is False
        assert is_same_date("2023-06-15", None) is False


class TestGetDateRangeLabel:
    """Tests for the get_date_range_label function."""

    def test_get_date_range_label_different_years(self):
        """Test get_date_range_label with dates in different years."""
        start = datetime.datetime(2022, 12, 15)
        end = datetime.datetime(2023, 6, 15)
        label = get_date_range_label(start, end)
        assert label == "15 Dec 2022 - 15 Jun 2023"

    def test_get_date_range_label_same_year_different_months(self):
        """Test get_date_range_label with dates in the same year but different months."""
        start = datetime.datetime(2023, 1, 15)
        end = datetime.datetime(2023, 6, 15)
        label = get_date_range_label(start, end)
        assert label == "15 Jan - 15 Jun 2023"

    def test_get_date_range_label_same_year_same_month_different_days(self):
        """Test get_date_range_label with dates in the same year and month but different days."""
        start = datetime.datetime(2023, 6, 1)
        end = datetime.datetime(2023, 6, 15)
        label = get_date_range_label(start, end)
        assert label == "1 - 15 Jun 2023"

    def test_get_date_range_label_same_date(self):
        """Test get_date_range_label with the same start and end date."""
        date = datetime.datetime(2023, 6, 15)
        label = get_date_range_label(date, date)
        assert label == "15 Jun 2023"

    def test_get_date_range_label_initial_true(self):
        """Test get_date_range_label with initial=True to get unoptimized format."""
        start = datetime.datetime(2023, 6, 1)
        end = datetime.datetime(2023, 6, 15)
        label = get_date_range_label(start, end, initial=True)
        assert label == "1 Jun 2023 - 15 Jun 2023"

    def test_get_date_range_label_invalid_dates(self):
        """Test get_date_range_label with invalid dates."""
        assert get_date_range_label(None, "2023-06-15") == "Invalid date"
        assert get_date_range_label("2023-06-01", None) == "Invalid date"

    def test_get_date_range_label_end_before_start(self):
        """Test get_date_range_label with end date before start date."""
        start = datetime.datetime(2023, 6, 15)
        end = datetime.datetime(2023, 6, 1)
        label = get_date_range_label(start, end)
        assert label == "Invalid date"


class TestAddSubtractTime:
    """Tests for the add_time and subtract_time functions."""

    @freeze_time("2023-05-15 12:30:45")
    def test_add_time_default_base_date(self):
        """Test add_time with default base_date (current time)."""
        result = add_time(days=1, hours=2, minutes=30)
        expected = datetime.datetime(2023, 5, 16, 15, 0, 45, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_add_time_custom_base_date(self):
        """Test add_time with a custom base_date."""
        base_date = datetime.datetime(2023, 5, 15, 12, 30, 45)
        result = add_time(days=1, hours=2, minutes=30, base_date=base_date)
        expected = datetime.datetime(2023, 5, 16, 15, 0, 45, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_add_time_years_months(self):
        """Test add_time with years and months."""
        base_date = datetime.datetime(2023, 5, 15, 12, 30, 45)
        result = add_time(years=1, months=2, base_date=base_date)
        expected = datetime.datetime(2024, 7, 15, 12, 30, 45, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_add_time_milliseconds(self):
        """Test add_time with milliseconds."""
        base_date = datetime.datetime(2023, 5, 15, 12, 30, 45)
        result = add_time(milliseconds=500, base_date=base_date)
        expected = datetime.datetime(2023, 5, 15, 12, 30, 45, 500000, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_add_time_leap_year(self):
        """Test add_time with leap year considerations."""
        # January 31 + 1 month should be February 28 in a non-leap year
        base_date = datetime.datetime(2023, 1, 31)
        result = add_time(months=1, base_date=base_date)
        expected = datetime.datetime(2023, 2, 28, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

        # January 31 + 1 month should be February 29 in a leap year
        base_date = datetime.datetime(2024, 1, 31)  # 2024 is a leap year
        result = add_time(months=1, base_date=base_date)
        expected = datetime.datetime(2024, 2, 29, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_add_time_invalid_base_date(self):
        """Test add_time with an invalid base_date."""
        # Should use current time if base_date is invalid
        with freeze_time("2023-05-15 12:30:45"):
            result = add_time(days=1, base_date=None)
            expected = datetime.datetime(2023, 5, 16, 12, 30, 45, tzinfo=DEFAULT_TIMEZONE)
            assert parser.parse(result) == expected

    @freeze_time("2023-05-15 12:30:45")
    def test_subtract_time_default_base_date(self):
        """Test subtract_time with default base_date (current time)."""
        result = subtract_time(days=1, hours=2, minutes=30)
        expected = datetime.datetime(2023, 5, 14, 10, 0, 45, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_subtract_time_custom_base_date(self):
        """Test subtract_time with a custom base_date."""
        base_date = datetime.datetime(2023, 5, 15, 12, 30, 45)
        result = subtract_time(days=1, hours=2, minutes=30, base_date=base_date)
        expected = datetime.datetime(2023, 5, 14, 10, 0, 45, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_subtract_time_years_months(self):
        """Test subtract_time with years and months."""
        base_date = datetime.datetime(2023, 5, 15, 12, 30, 45)
        result = subtract_time(years=1, months=2, base_date=base_date)
        expected = datetime.datetime(2022, 3, 15, 12, 30, 45, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_subtract_time_milliseconds(self):
        """Test subtract_time with milliseconds."""
        base_date = datetime.datetime(2023, 5, 15, 12, 30, 45, 500000)
        result = subtract_time(milliseconds=500, base_date=base_date)
        expected = datetime.datetime(2023, 5, 15, 12, 30, 45, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

    def test_subtract_time_month_edge_case(self):
        """Test subtract_time with month edge cases."""
        # March 31 - 1 month should be February 28 in a non-leap year
        base_date = datetime.datetime(2023, 3, 31)
        result = subtract_time(months=1, base_date=base_date)
        expected = datetime.datetime(2023, 2, 28, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected

        # March 31 - 1 month should be February 29 in a leap year
        base_date = datetime.datetime(2024, 3, 31)  # 2024 is a leap year
        result = subtract_time(months=1, base_date=base_date)
        expected = datetime.datetime(2024, 2, 29, tzinfo=DEFAULT_TIMEZONE)
        assert parser.parse(result) == expected


class TestParseIsoDatetime:
    """Tests for the parse_iso_datetime function."""

    def test_parse_iso_datetime_valid(self):
        """Test parse_iso_datetime with a valid ISO 8601 string."""
        dt_str = "2023-05-15T12:30:45Z"
        result = parse_iso_datetime(dt_str)
        expected = datetime.datetime(2023, 5, 15, 12, 30, 45, tzinfo=pytz.UTC)
        assert result == expected

    def test_parse_iso_datetime_with_timezone(self):
        """Test parse_iso_datetime with a timezone-aware ISO 8601 string."""
        dt_str = "2023-05-15T12:30:45+02:00"
        result = parse_iso_datetime(dt_str)
        # The result should be timezone-aware with the specified offset
        assert result.tzinfo is not None
        assert result.tzname() == "+02:00"
        assert result.hour == 12

    def test_parse_iso_datetime_invalid(self):
        """Test parse_iso_datetime with an invalid string."""
        assert parse_iso_datetime("not a date") is None
        assert parse_iso_datetime(None) is None


class TestCalculateProcessingTime:
    """Tests for the calculate_processing_time function."""

    def test_calculate_processing_time_valid(self):
        """Test calculate_processing_time with valid start and end times."""
        start_time = datetime.datetime(2023, 5, 15, 12, 30, 0)
        end_time = datetime.datetime(2023, 5, 15, 12, 30, 30)  # 30 seconds later
        result = calculate_processing_time(start_time, end_time)
        
        assert result["valid"] is True
        assert result["seconds"] == 30
        assert result["milliseconds"] == 30000
        assert result["formatted"] == "30.0s"

    def test_calculate_processing_time_milliseconds(self):
        """Test calculate_processing_time with a time difference in milliseconds."""
        start_time = datetime.datetime(2023, 5, 15, 12, 30, 0)
        end_time = datetime.datetime(2023, 5, 15, 12, 30, 0, 500000)  # 500ms later
        result = calculate_processing_time(start_time, end_time)
        
        assert result["valid"] is True
        assert result["seconds"] == 0.5
        assert result["milliseconds"] == 500
        assert result["formatted"] == "500ms"

    def test_calculate_processing_time_minutes(self):
        """Test calculate_processing_time with a time difference in minutes."""
        start_time = datetime.datetime(2023, 5, 15, 12, 30, 0)
        end_time = datetime.datetime(2023, 5, 15, 12, 32, 30)  # 2 minutes and 30 seconds later
        result = calculate_processing_time(start_time, end_time)
        
        assert result["valid"] is True
        assert result["seconds"] == 150
        assert result["milliseconds"] == 150000
        assert result["formatted"] == "2m 30.0s"

    def test_calculate_processing_time_hours(self):
        """Test calculate_processing_time with a time difference in hours."""
        start_time = datetime.datetime(2023, 5, 15, 12, 30, 0)
        end_time = datetime.datetime(2023, 5, 15, 14, 45, 15)  # 2 hours, 15 minutes, and 15 seconds later
        result = calculate_processing_time(start_time, end_time)
        
        assert result["valid"] is True
        assert result["seconds"] == 8115
        assert result["milliseconds"] == 8115000
        assert result["formatted"] == "2h 15m 15.0s"

    def test_calculate_processing_time_invalid_dates(self):
        """Test calculate_processing_time with invalid dates."""
        result = calculate_processing_time(None, "2023-05-15T12:30:30Z")
        assert result["valid"] is False
        assert result["error"] == "Invalid date"
        
        result = calculate_processing_time("2023-05-15T12:30:00Z", None)
        assert result["valid"] is False
        assert result["error"] == "Invalid date"

    def test_calculate_processing_time_timezone_aware(self):
        """Test calculate_processing_time with timezone-aware datetimes."""
        start_time = datetime.datetime(2023, 5, 15, 12, 30, 0, tzinfo=pytz.UTC)
        end_time = datetime.datetime(2023, 5, 15, 14, 30, 0, tzinfo=pytz.UTC)  # 2 hours later
        result = calculate_processing_time(start_time, end_time)
        
        assert result["valid"] is True
        assert result["seconds"] == 7200
        assert result["milliseconds"] == 7200000
        assert result["formatted"] == "2h 0m 0.0s"

    def test_calculate_processing_time_different_timezones(self):
        """Test calculate_processing_time with datetimes in different timezones."""
        start_time = datetime.datetime(2023, 5, 15, 12, 30, 0, tzinfo=pytz.UTC)
        # 2 hours later in UTC, but expressed in EST (UTC-5)
        end_time = datetime.datetime(2023, 5, 15, 9, 30, 0, tzinfo=pytz.timezone('US/Eastern'))
        result = calculate_processing_time(start_time, end_time)
        
        assert result["valid"] is True
        # The difference should be 2 hours (7200 seconds) regardless of timezone representation
        assert result["seconds"] == 7200
        assert result["milliseconds"] == 7200000
        assert result["formatted"] == "2h 0m 0.0s"


class TestCalculateDocumentAge:
    """Tests for the calculate_document_age function."""

    @freeze_time("2023-05-15 12:30:45")
    def test_calculate_document_age_minutes(self):
        """Test calculate_document_age with a document age in minutes."""
        # Document from 30 minutes ago
        doc_date = datetime.datetime.now() - datetime.timedelta(minutes=30)
        result = calculate_document_age(doc_date)
        
        assert result["valid"] is True
        assert result["days"] == 0
        assert result["formatted"] == "30 minutes"

    @freeze_time("2023-05-15 12:30:45")
    def test_calculate_document_age_hours(self):
        """Test calculate_document_age with a document age in hours."""
        # Document from 3 hours ago
        doc_date = datetime.datetime.now() - datetime.timedelta(hours=3)
        result = calculate_document_age(doc_date)
        
        assert result["valid"] is True
        assert result["days"] == 0
        assert result["formatted"] == "3 hours"

    @freeze_time("2023-05-15 12:30:45")
    def test_calculate_document_age_days(self):
        """Test calculate_document_age with a document age in days."""
        # Document from 5 days ago
        doc_date = datetime.datetime.now() - datetime.timedelta(days=5)
        result = calculate_document_age(doc_date)
        
        assert result["valid"] is True
        assert result["days"] == 5
        assert result["formatted"] == "5 days"

    @freeze_time("2023-05-15 12:30:45")
    def test_calculate_document_age_months(self):
        """Test calculate_document_age with a document age in months."""
        # Document from 2 months ago (approximately 60 days)
        doc_date = datetime.datetime.now() - datetime.timedelta(days=60)
        result = calculate_document_age(doc_date)
        
        assert result["valid"] is True
        assert result["days"] == 60
        assert result["formatted"] == "2 months"

    @freeze_time("2023-05-15 12:30:45")
    def test_calculate_document_age_years(self):
        """Test calculate_document_age with a document age in years."""
        # Document from 1 year and 2 months ago (approximately 425 days)
        doc_date = datetime.datetime.now() - datetime.timedelta(days=425)
        result = calculate_document_age(doc_date)
        
        assert result["valid"] is True
        assert result["days"] == 425
        assert result["formatted"] == "1 year 2 months"

    @freeze_time("2023-05-15 12:30:45")
    def test_calculate_document_age_years_no_months(self):
        """Test calculate_document_age with a document age in years with no remaining months."""
        # Document from 2 years ago (approximately 730 days)
        doc_date = datetime.datetime.now() - datetime.timedelta(days=730)
        result = calculate_document_age(doc_date)
        
        assert result["valid"] is True
        assert result["days"] == 730
        assert result["formatted"] == "2 years"

    def test_calculate_document_age_invalid_date(self):
        """Test calculate_document_age with an invalid date."""
        result = calculate_document_age(None)
        
        assert result["valid"] is False
        assert result["error"] == "Invalid date"
        assert result["days"] == 0
        assert result["formatted"] == "Unknown"

    @freeze_time("2023-05-15 12:30:45")
    def test_calculate_document_age_timezone_aware(self):
        """Test calculate_document_age with a timezone-aware datetime."""
        # Document from 3 days ago with UTC timezone
        doc_date = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=3)
        result = calculate_document_age(doc_date)
        
        assert result["valid"] is True
        assert result["days"] == 3
        assert result["formatted"] == "3 days"


class TestTimestampFunctions:
    """Tests for the get_processing_timestamp, get_log_timestamp, and get_expiry_timestamp functions."""

    @freeze_time("2023-05-15 12:30:45")
    def test_get_processing_timestamp(self):
        """Test get_processing_timestamp returns the correct ISO and Unix timestamps."""
        iso_timestamp, unix_timestamp = get_processing_timestamp()
        
        assert iso_timestamp == "2023-05-15T12:30:45.000Z"
        assert unix_timestamp == int(datetime.datetime(2023, 5, 15, 12, 30, 45).timestamp())

    @freeze_time("2023-05-15 12:30:45.123456")
    def test_get_log_timestamp(self):
        """Test get_log_timestamp returns the correct log format timestamp."""
        log_timestamp = get_log_timestamp()
        
        assert log_timestamp == "2023-05-15 12:30:45.123456"

    @freeze_time("2023-05-15 12:30:45")
    def test_get_expiry_timestamp(self):
        """Test get_expiry_timestamp returns the correct expiry timestamps."""
        # Test with 1 hour TTL (3600 seconds)
        iso_timestamp, unix_timestamp = get_expiry_timestamp(3600)
        
        expected_dt = datetime.datetime(2023, 5, 15, 13, 30, 45, tzinfo=DEFAULT_TIMEZONE)
        assert iso_timestamp == "2023-05-15T13:30:45.000Z"
        assert unix_timestamp == int(expected_dt.timestamp())

    @freeze_time("2023-05-15 12:30:45")
    def test_get_expiry_timestamp_days(self):
        """Test get_expiry_timestamp with a TTL of multiple days."""
        # Test with 2 days TTL (172800 seconds)
        iso_timestamp, unix_timestamp = get_expiry_timestamp(172800)
        
        expected_dt = datetime.datetime(2023, 5, 17, 12, 30, 45, tzinfo=DEFAULT_TIMEZONE)
        assert iso_timestamp == "2023-05-17T12:30:45.000Z"
        assert unix_timestamp == int(expected_dt.timestamp())


class TestTimezoneHandling:
    """Tests for timezone handling consistency across all functions."""

    def test_default_timezone_is_utc(self):
        """Test that the default timezone is UTC."""
        assert DEFAULT_TIMEZONE == pytz.UTC

    @freeze_time("2023-05-15 12:30:45")
    def test_timezone_consistency_in_timestamp_generation(self):
        """Test timezone consistency in timestamp generation functions."""
        # All timestamp generation functions should use the same timezone (UTC by default)
        timestamp1 = get_current_timestamp()
        timestamp2 = get_processing_timestamp()[0]
        timestamp3 = get_log_timestamp()
        
        dt1 = parser.parse(timestamp1)
        dt2 = parser.parse(timestamp2)
        dt3 = parser.parse(timestamp3)
        
        # All should represent the same point in time
        assert dt1.replace(microsecond=0) == dt2.replace(microsecond=0)
        assert dt1.replace(microsecond=0) == dt3.replace(microsecond=0, tzinfo=pytz.UTC)

    def test_timezone_handling_in_date_comparison(self):
        """Test timezone handling in date comparison functions."""
        # Create two datetimes representing the same point in time in different timezones
        dt1 = datetime.datetime(2023, 5, 15, 12, 30, 45, tzinfo=pytz.UTC)
        dt2 = datetime.datetime(2023, 5, 15, 7, 30, 45, tzinfo=pytz.timezone('US/Eastern'))  # UTC-5
        
        # They should be considered the same time
        assert is_same_date(dt1, dt2, "second") is True
        assert is_date_after(dt1, dt2) is False
        assert is_date_after(dt2, dt1) is False

    def test_timezone_handling_in_duration_calculation(self):
        """Test timezone handling in duration calculation functions."""
        # Create start and end times in different timezones
        start = datetime.datetime(2023, 5, 15, 12, 30, 0, tzinfo=pytz.UTC)
        end = datetime.datetime(2023, 5, 15, 8, 30, 0, tzinfo=pytz.timezone('US/Eastern'))  # UTC-4 during DST
        
        # The duration should be 1 hour (3600 seconds)
        result = calculate_processing_time(start, end)
        assert result["valid"] is True
        assert result["seconds"] == 3600
        assert result["formatted"] == "1h 0m 0.0s"


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])