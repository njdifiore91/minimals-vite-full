#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Time utilities for the OCR Service.

This module provides utility functions for timestamp generation, date comparison,
duration calculation, and time formatting. It's essential for consistent timestamp
handling in logs, message publishing, and document metadata.

Functions:
    get_current_timestamp: Get the current timestamp in ISO 8601 format
    format_datetime: Format a datetime object to a string with a specified template
    format_date: Format a date object to a string with a specified template
    format_time: Format a time object to a string with a specified template
    format_timestamp: Convert a datetime object to a Unix timestamp
    format_time_to_now: Get the time difference from now as a human-readable string
    is_date_between: Check if a date is between two other dates
    is_date_after: Check if a date is after another date
    is_same_date: Check if two dates are the same
    add_time: Add a duration to the current time
    subtract_time: Subtract a duration from the current time
    parse_iso_datetime: Parse an ISO 8601 datetime string
    calculate_processing_time: Calculate the processing time between two timestamps
    calculate_document_age: Calculate the age of a document
    is_valid_date: Check if a date is valid
    get_date_range_label: Get a formatted date range label

Requirements:
    - OCR Service must update document metadata with processing timestamps
    - Service must implement comprehensive logging with timestamps
    - Messages must be serialized in standardized JSON format with consistent date handling
"""

import datetime
import time
from typing import Any, Dict, Optional, Tuple, Union
from dateutil import parser
import pytz

# Default timezone (UTC)
DEFAULT_TIMEZONE = pytz.UTC

# Format patterns
FORMAT_PATTERNS = {
    "datetime": "%d %b %Y %I:%M %p",  # 17 Apr 2022 12:00 AM
    "date": "%d %b %Y",  # 17 Apr 2022
    "time": "%I:%M %p",  # 12:00 AM
    "iso8601": "%Y-%m-%dT%H:%M:%S.%fZ",  # 2022-04-17T12:00:00.000Z
    "iso8601_with_tz": "%Y-%m-%dT%H:%M:%S%z",  # 2022-04-17T12:00:00+00:00
    "log_timestamp": "%Y-%m-%d %H:%M:%S.%f",  # 2022-04-17 12:00:00.000
    "split": {
        "datetime": "%d/%m/%Y %I:%M %p",  # 17/04/2022 12:00 AM
        "date": "%d/%m/%Y",  # 17/04/2022
    },
    "param_case": {
        "datetime": "%d-%m-%Y %I:%M %p",  # 17-04-2022 12:00 AM
        "date": "%d-%m-%Y",  # 17-04-2022
    },
}

# Type definitions
DateType = Union[datetime.datetime, datetime.date, str, int, float, None]


def is_valid_date(date: DateType) -> bool:
    """
    Check if a date is valid.
    
    Args:
        date: The date to check. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        bool: True if the date is valid, False otherwise.
    """
    if date is None:
        return False
    
    try:
        if isinstance(date, (datetime.datetime, datetime.date)):
            return True
        elif isinstance(date, str):
            parser.parse(date)
            return True
        elif isinstance(date, (int, float)):
            datetime.datetime.fromtimestamp(date)
            return True
        return False
    except (ValueError, TypeError, OverflowError):
        return False


def _ensure_datetime(date: DateType) -> Optional[datetime.datetime]:
    """
    Convert various date formats to a datetime object.
    
    Args:
        date: The date to convert. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        datetime.datetime: The converted datetime object, or None if the date is invalid.
    """
    if not is_valid_date(date):
        return None
    
    if isinstance(date, datetime.datetime):
        return date
    elif isinstance(date, datetime.date):
        return datetime.datetime.combine(date, datetime.time.min)
    elif isinstance(date, str):
        return parser.parse(date)
    elif isinstance(date, (int, float)):
        return datetime.datetime.fromtimestamp(date)
    
    return None


def get_current_timestamp(timezone: Optional[pytz.timezone] = None) -> str:
    """
    Get the current timestamp in ISO 8601 format.
    
    Args:
        timezone: The timezone to use. Defaults to UTC.
        
    Returns:
        str: The current timestamp in ISO 8601 format.
    """
    tz = timezone or DEFAULT_TIMEZONE
    now = datetime.datetime.now(tz)
    return now.strftime(FORMAT_PATTERNS["iso8601"])


def format_datetime(date: DateType, template: Optional[str] = None) -> str:
    """
    Format a datetime object to a string with a specified template.
    
    Args:
        date: The date to format. Can be a datetime object, string, timestamp, or None.
        template: The format template to use. Defaults to FORMAT_PATTERNS["datetime"].
        
    Returns:
        str: The formatted datetime string, or "Invalid date" if the date is invalid.
    """
    dt = _ensure_datetime(date)
    if dt is None:
        return "Invalid date"
    
    return dt.strftime(template or FORMAT_PATTERNS["datetime"])


def format_date(date: DateType, template: Optional[str] = None) -> str:
    """
    Format a date object to a string with a specified template.
    
    Args:
        date: The date to format. Can be a datetime object, string, timestamp, or None.
        template: The format template to use. Defaults to FORMAT_PATTERNS["date"].
        
    Returns:
        str: The formatted date string, or "Invalid date" if the date is invalid.
    """
    dt = _ensure_datetime(date)
    if dt is None:
        return "Invalid date"
    
    return dt.strftime(template or FORMAT_PATTERNS["date"])


def format_time(date: DateType, template: Optional[str] = None) -> str:
    """
    Format a time object to a string with a specified template.
    
    Args:
        date: The date to format. Can be a datetime object, string, timestamp, or None.
        template: The format template to use. Defaults to FORMAT_PATTERNS["time"].
        
    Returns:
        str: The formatted time string, or "Invalid date" if the date is invalid.
    """
    dt = _ensure_datetime(date)
    if dt is None:
        return "Invalid date"
    
    return dt.strftime(template or FORMAT_PATTERNS["time"])


def format_timestamp(date: DateType) -> Union[int, str]:
    """
    Convert a datetime object to a Unix timestamp.
    
    Args:
        date: The date to convert. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        int: The Unix timestamp, or "Invalid date" if the date is invalid.
    """
    dt = _ensure_datetime(date)
    if dt is None:
        return "Invalid date"
    
    return int(dt.timestamp())


def format_time_to_now(date: DateType) -> str:
    """
    Get the time difference from now as a human-readable string.
    
    Args:
        date: The date to compare. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        str: The time difference as a human-readable string, or "Invalid date" if the date is invalid.
    """
    dt = _ensure_datetime(date)
    if dt is None:
        return "Invalid date"
    
    now = datetime.datetime.now(DEFAULT_TIMEZONE)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
    
    diff = now - dt
    
    # Convert to a human-readable string
    seconds = diff.total_seconds()
    if seconds < 60:
        return "a few seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''}"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''}"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''}"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''}"


def is_date_between(
    input_date: DateType, start_date: DateType, end_date: DateType
) -> bool:
    """
    Check if a date is between two other dates.
    
    Args:
        input_date: The date to check. Can be a datetime object, string, timestamp, or None.
        start_date: The start date. Can be a datetime object, string, timestamp, or None.
        end_date: The end date. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        bool: True if the input date is between the start and end dates, False otherwise.
    """
    input_dt = _ensure_datetime(input_date)
    start_dt = _ensure_datetime(start_date)
    end_dt = _ensure_datetime(end_date)
    
    if input_dt is None or start_dt is None or end_dt is None:
        return False
    
    return start_dt <= input_dt <= end_dt


def is_date_after(start_date: DateType, end_date: DateType) -> bool:
    """
    Check if a date is after another date.
    
    Args:
        start_date: The start date. Can be a datetime object, string, timestamp, or None.
        end_date: The end date. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        bool: True if the start date is after the end date, False otherwise.
    """
    start_dt = _ensure_datetime(start_date)
    end_dt = _ensure_datetime(end_date)
    
    if start_dt is None or end_dt is None:
        return False
    
    return start_dt > end_dt


def is_same_date(
    start_date: DateType, end_date: DateType, unit_to_compare: str = "year"
) -> bool:
    """
    Check if two dates are the same based on a specified unit.
    
    Args:
        start_date: The start date. Can be a datetime object, string, timestamp, or None.
        end_date: The end date. Can be a datetime object, string, timestamp, or None.
        unit_to_compare: The unit to compare. Can be "year", "month", "day", "hour", "minute", or "second".
        
    Returns:
        bool: True if the dates are the same based on the specified unit, False otherwise.
    """
    start_dt = _ensure_datetime(start_date)
    end_dt = _ensure_datetime(end_date)
    
    if start_dt is None or end_dt is None:
        return False
    
    if unit_to_compare == "year":
        return start_dt.year == end_dt.year
    elif unit_to_compare == "month":
        return (start_dt.year, start_dt.month) == (end_dt.year, end_dt.month)
    elif unit_to_compare == "day":
        return (start_dt.year, start_dt.month, start_dt.day) == (end_dt.year, end_dt.month, end_dt.day)
    elif unit_to_compare == "hour":
        return (
            start_dt.year, start_dt.month, start_dt.day, start_dt.hour
        ) == (
            end_dt.year, end_dt.month, end_dt.day, end_dt.hour
        )
    elif unit_to_compare == "minute":
        return (
            start_dt.year, start_dt.month, start_dt.day, start_dt.hour, start_dt.minute
        ) == (
            end_dt.year, end_dt.month, end_dt.day, end_dt.hour, end_dt.minute
        )
    elif unit_to_compare == "second":
        return (
            start_dt.year, start_dt.month, start_dt.day, start_dt.hour, start_dt.minute, start_dt.second
        ) == (
            end_dt.year, end_dt.month, end_dt.day, end_dt.hour, end_dt.minute, end_dt.second
        )
    
    return False


def get_date_range_label(
    start_date: DateType, end_date: DateType, initial: bool = False
) -> str:
    """
    Get a formatted date range label.
    
    Args:
        start_date: The start date. Can be a datetime object, string, timestamp, or None.
        end_date: The end date. Can be a datetime object, string, timestamp, or None.
        initial: Whether to return the initial format without optimization.
        
    Returns:
        str: The formatted date range label, or "Invalid date" if either date is invalid.
    """
    start_dt = _ensure_datetime(start_date)
    end_dt = _ensure_datetime(end_date)
    
    if start_dt is None or end_dt is None or is_date_after(start_dt, end_dt):
        return "Invalid date"
    
    label = f"{format_date(start_dt)} - {format_date(end_dt)}"
    
    if initial:
        return label
    
    is_same_year = is_same_date(start_dt, end_dt, "year")
    is_same_month = is_same_date(start_dt, end_dt, "month")
    is_same_day = is_same_date(start_dt, end_dt, "day")
    
    if is_same_year and not is_same_month:
        label = f"{format_date(start_dt, '%d %b')} - {format_date(end_dt)}"
    elif is_same_year and is_same_month and not is_same_day:
        label = f"{format_date(start_dt, '%d')} - {format_date(end_dt)}"
    elif is_same_year and is_same_month and is_same_day:
        label = f"{format_date(end_dt)}"
    
    return label


def add_time(
    years: int = 0,
    months: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    milliseconds: int = 0,
    base_date: Optional[DateType] = None,
) -> str:
    """
    Add a duration to a date and return the result in ISO 8601 format.
    
    Args:
        years: The number of years to add.
        months: The number of months to add.
        days: The number of days to add.
        hours: The number of hours to add.
        minutes: The number of minutes to add.
        seconds: The number of seconds to add.
        milliseconds: The number of milliseconds to add.
        base_date: The base date to add to. Defaults to the current time.
        
    Returns:
        str: The resulting date in ISO 8601 format.
    """
    if base_date is None:
        dt = datetime.datetime.now(DEFAULT_TIMEZONE)
    else:
        dt = _ensure_datetime(base_date)
        if dt is None:
            dt = datetime.datetime.now(DEFAULT_TIMEZONE)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
    
    # Add years and months
    if years != 0 or months != 0:
        month = dt.month - 1 + months + years * 12
        year = dt.year + month // 12
        month = month % 12 + 1
        day = min(dt.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        dt = dt.replace(year=year, month=month, day=day)
    
    # Add days, hours, minutes, seconds, and milliseconds
    dt = dt + datetime.timedelta(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        milliseconds=milliseconds,
    )
    
    return dt.strftime(FORMAT_PATTERNS["iso8601_with_tz"])


def subtract_time(
    years: int = 0,
    months: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    milliseconds: int = 0,
    base_date: Optional[DateType] = None,
) -> str:
    """
    Subtract a duration from a date and return the result in ISO 8601 format.
    
    Args:
        years: The number of years to subtract.
        months: The number of months to subtract.
        days: The number of days to subtract.
        hours: The number of hours to subtract.
        minutes: The number of minutes to subtract.
        seconds: The number of seconds to subtract.
        milliseconds: The number of milliseconds to subtract.
        base_date: The base date to subtract from. Defaults to the current time.
        
    Returns:
        str: The resulting date in ISO 8601 format.
    """
    return add_time(
        years=-years,
        months=-months,
        days=-days,
        hours=-hours,
        minutes=-minutes,
        seconds=-seconds,
        milliseconds=-milliseconds,
        base_date=base_date,
    )


def parse_iso_datetime(date_string: str) -> Optional[datetime.datetime]:
    """
    Parse an ISO 8601 datetime string.
    
    Args:
        date_string: The ISO 8601 datetime string to parse.
        
    Returns:
        datetime.datetime: The parsed datetime object, or None if the string is invalid.
    """
    try:
        return parser.parse(date_string)
    except (ValueError, TypeError):
        return None


def calculate_processing_time(start_time: DateType, end_time: DateType) -> Dict[str, Any]:
    """
    Calculate the processing time between two timestamps.
    
    Args:
        start_time: The start time. Can be a datetime object, string, timestamp, or None.
        end_time: The end time. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        Dict[str, Any]: A dictionary containing the processing time in various formats.
    """
    start_dt = _ensure_datetime(start_time)
    end_dt = _ensure_datetime(end_time)
    
    if start_dt is None or end_dt is None:
        return {
            "valid": False,
            "error": "Invalid date",
            "seconds": 0,
            "milliseconds": 0,
            "formatted": "0s",
        }
    
    # Ensure both datetimes have timezone information
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=DEFAULT_TIMEZONE)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=DEFAULT_TIMEZONE)
    
    diff = end_dt - start_dt
    seconds = diff.total_seconds()
    milliseconds = int(seconds * 1000)
    
    # Format the duration
    if seconds < 1:
        formatted = f"{milliseconds}ms"
    elif seconds < 60:
        formatted = f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        remaining_seconds = seconds % 60
        formatted = f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds / 3600)
        remaining_seconds = seconds % 3600
        minutes = int(remaining_seconds / 60)
        remaining_seconds = remaining_seconds % 60
        formatted = f"{hours}h {minutes}m {remaining_seconds:.1f}s"
    
    return {
        "valid": True,
        "seconds": seconds,
        "milliseconds": milliseconds,
        "formatted": formatted,
    }


def calculate_document_age(document_date: DateType) -> Dict[str, Any]:
    """
    Calculate the age of a document.
    
    Args:
        document_date: The document date. Can be a datetime object, string, timestamp, or None.
        
    Returns:
        Dict[str, Any]: A dictionary containing the document age in various formats.
    """
    doc_dt = _ensure_datetime(document_date)
    
    if doc_dt is None:
        return {
            "valid": False,
            "error": "Invalid date",
            "days": 0,
            "formatted": "Unknown",
        }
    
    # Ensure the datetime has timezone information
    if doc_dt.tzinfo is None:
        doc_dt = doc_dt.replace(tzinfo=DEFAULT_TIMEZONE)
    
    now = datetime.datetime.now(DEFAULT_TIMEZONE)
    diff = now - doc_dt
    days = diff.days
    
    # Format the age
    if days < 1:
        hours = int(diff.total_seconds() / 3600)
        if hours < 1:
            minutes = int(diff.total_seconds() / 60)
            formatted = f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            formatted = f"{hours} hour{'s' if hours != 1 else ''}"
    elif days < 30:
        formatted = f"{days} day{'s' if days != 1 else ''}"
    elif days < 365:
        months = days // 30
        formatted = f"{months} month{'s' if months != 1 else ''}"
    else:
        years = days // 365
        remaining_days = days % 365
        months = remaining_days // 30
        if months > 0:
            formatted = f"{years} year{'s' if years != 1 else ''} {months} month{'s' if months != 1 else ''}"
        else:
            formatted = f"{years} year{'s' if years != 1 else ''}"
    
    return {
        "valid": True,
        "days": days,
        "formatted": formatted,
    }


def get_processing_timestamp() -> Tuple[str, int]:
    """
    Get a timestamp for processing operations with both ISO format and Unix timestamp.
    
    Returns:
        Tuple[str, int]: A tuple containing the ISO 8601 timestamp and Unix timestamp.
    """
    now = datetime.datetime.now(DEFAULT_TIMEZONE)
    iso_timestamp = now.strftime(FORMAT_PATTERNS["iso8601"])
    unix_timestamp = int(now.timestamp())
    
    return iso_timestamp, unix_timestamp


def get_log_timestamp() -> str:
    """
    Get a timestamp for logging purposes.
    
    Returns:
        str: The current timestamp in log format.
    """
    now = datetime.datetime.now(DEFAULT_TIMEZONE)
    return now.strftime(FORMAT_PATTERNS["log_timestamp"])


def get_expiry_timestamp(ttl_seconds: int) -> Tuple[str, int]:
    """
    Calculate an expiry timestamp based on a TTL in seconds.
    
    Args:
        ttl_seconds: The time-to-live in seconds.
        
    Returns:
        Tuple[str, int]: A tuple containing the ISO 8601 expiry timestamp and Unix timestamp.
    """
    now = datetime.datetime.now(DEFAULT_TIMEZONE)
    expiry = now + datetime.timedelta(seconds=ttl_seconds)
    iso_timestamp = expiry.strftime(FORMAT_PATTERNS["iso8601"])
    unix_timestamp = int(expiry.timestamp())
    
    return iso_timestamp, unix_timestamp