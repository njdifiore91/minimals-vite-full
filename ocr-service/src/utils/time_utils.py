#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Time utilities for the OCR Service.

This module provides functions for timestamp generation, date comparison,
duration calculation, and time formatting. It's essential for consistent
timestamp handling in logs, message publishing, and document metadata.
"""

import datetime
import time
from typing import Optional, Union, Dict, Any, Tuple, List
from dateutil import parser, tz
from dateutil.relativedelta import relativedelta

# Type aliases for clarity
Timestamp = Union[datetime.datetime, str, int, float]
DurationDict = Dict[str, int]

# Constants for formatting patterns
FORMAT_PATTERNS = {
    'datetime': '%d %b %Y %I:%M %p',  # 17 Apr 2022 12:00 AM
    'date': '%d %b %Y',                # 17 Apr 2022
    'time': '%I:%M %p',                # 12:00 AM
    'iso8601': '%Y-%m-%dT%H:%M:%S.%f%z',  # 2022-04-17T12:00:00.000000+0000
    'split': {
        'datetime': '%d/%m/%Y %I:%M %p',  # 17/04/2022 12:00 AM
        'date': '%d/%m/%Y',              # 17/04/2022
    },
    'param_case': {
        'datetime': '%d-%m-%Y %I:%M %p',  # 17-04-2022 12:00 AM
        'date': '%d-%m-%Y',              # 17-04-2022
    },
    'log': '%Y-%m-%d %H:%M:%S.%f',     # 2022-04-17 12:00:00.000000
}


def is_valid_date(date: Timestamp) -> bool:
    """
    Check if a date is valid.
    
    Args:
        date: The date to check, can be a datetime object, string, or timestamp
        
    Returns:
        bool: True if the date is valid, False otherwise
    """
    if date is None:
        return False
    
    try:
        if isinstance(date, (int, float)):
            # Convert timestamp to datetime
            datetime.datetime.fromtimestamp(date)
        elif isinstance(date, str):
            # Parse string to datetime
            parser.parse(date)
        elif isinstance(date, datetime.datetime):
            # Already a datetime object
            pass
        else:
            return False
        return True
    except (ValueError, TypeError, OverflowError):
        return False


def to_datetime(date: Timestamp) -> Optional[datetime.datetime]:
    """
    Convert various date formats to a datetime object.
    
    Args:
        date: The date to convert, can be a datetime object, string, or timestamp
        
    Returns:
        datetime.datetime or None: The converted datetime object, or None if invalid
    """
    if not is_valid_date(date):
        return None
    
    if isinstance(date, datetime.datetime):
        return date
    elif isinstance(date, (int, float)):
        return datetime.datetime.fromtimestamp(date)
    elif isinstance(date, str):
        return parser.parse(date)
    
    return None


def get_current_timestamp() -> datetime.datetime:
    """
    Get the current timestamp with timezone information.
    
    Returns:
        datetime.datetime: Current datetime with timezone
    """
    return datetime.datetime.now(tz.tzlocal())


def get_utc_timestamp() -> datetime.datetime:
    """
    Get the current UTC timestamp.
    
    Returns:
        datetime.datetime: Current UTC datetime
    """
    return datetime.datetime.now(tz.UTC)


def format_datetime(date: Timestamp, template: Optional[str] = None) -> str:
    """
    Format a date as a datetime string.
    
    Args:
        date: The date to format
        template: Optional format template
        
    Returns:
        str: Formatted datetime string or 'Invalid date' if invalid
    """
    dt = to_datetime(date)
    if dt is None:
        return 'Invalid date'
    
    template = template or FORMAT_PATTERNS['datetime']
    return dt.strftime(template)


def format_date(date: Timestamp, template: Optional[str] = None) -> str:
    """
    Format a date as a date string (without time).
    
    Args:
        date: The date to format
        template: Optional format template
        
    Returns:
        str: Formatted date string or 'Invalid date' if invalid
    """
    dt = to_datetime(date)
    if dt is None:
        return 'Invalid date'
    
    template = template or FORMAT_PATTERNS['date']
    return dt.strftime(template)


def format_time(date: Timestamp, template: Optional[str] = None) -> str:
    """
    Format a date as a time string (without date).
    
    Args:
        date: The date to format
        template: Optional format template
        
    Returns:
        str: Formatted time string or 'Invalid date' if invalid
    """
    dt = to_datetime(date)
    if dt is None:
        return 'Invalid date'
    
    template = template or FORMAT_PATTERNS['time']
    return dt.strftime(template)


def format_iso8601(date: Timestamp) -> str:
    """
    Format a date as an ISO 8601 string.
    
    Args:
        date: The date to format
        
    Returns:
        str: ISO 8601 formatted string or 'Invalid date' if invalid
    """
    dt = to_datetime(date)
    if dt is None:
        return 'Invalid date'
    
    # Ensure timezone information is present
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.UTC)
    
    return dt.isoformat()


def get_timestamp_ms(date: Optional[Timestamp] = None) -> int:
    """
    Get a timestamp in milliseconds.
    
    Args:
        date: Optional date to convert, defaults to current time
        
    Returns:
        int: Timestamp in milliseconds
    """
    if date is None:
        return int(time.time() * 1000)
    
    dt = to_datetime(date)
    if dt is None:
        return 0
    
    return int(dt.timestamp() * 1000)


def is_between(
    input_date: Timestamp,
    start_date: Timestamp,
    end_date: Timestamp
) -> bool:
    """
    Check if a date is between two other dates (inclusive).
    
    Args:
        input_date: The date to check
        start_date: The start date of the range
        end_date: The end date of the range
        
    Returns:
        bool: True if the date is between start and end, False otherwise
    """
    input_dt = to_datetime(input_date)
    start_dt = to_datetime(start_date)
    end_dt = to_datetime(end_date)
    
    if None in (input_dt, start_dt, end_dt):
        return False
    
    return start_dt <= input_dt <= end_dt


def is_after(date1: Timestamp, date2: Timestamp) -> bool:
    """
    Check if date1 is after date2.
    
    Args:
        date1: The first date
        date2: The second date
        
    Returns:
        bool: True if date1 is after date2, False otherwise
    """
    dt1 = to_datetime(date1)
    dt2 = to_datetime(date2)
    
    if None in (dt1, dt2):
        return False
    
    return dt1 > dt2


def is_same(
    date1: Timestamp,
    date2: Timestamp,
    unit: str = 'day'
) -> bool:
    """
    Check if two dates are the same at the specified unit level.
    
    Args:
        date1: The first date
        date2: The second date
        unit: The unit to compare ('year', 'month', 'day', 'hour', 'minute', 'second')
        
    Returns:
        bool: True if dates are the same at the specified unit, False otherwise
    """
    dt1 = to_datetime(date1)
    dt2 = to_datetime(date2)
    
    if None in (dt1, dt2):
        return False
    
    if unit == 'year':
        return dt1.year == dt2.year
    elif unit == 'month':
        return (dt1.year, dt1.month) == (dt2.year, dt2.month)
    elif unit == 'day':
        return (dt1.year, dt1.month, dt1.day) == (dt2.year, dt2.month, dt2.day)
    elif unit == 'hour':
        return (dt1.year, dt1.month, dt1.day, dt1.hour) == (dt2.year, dt2.month, dt2.day, dt2.hour)
    elif unit == 'minute':
        return (dt1.year, dt1.month, dt1.day, dt1.hour, dt1.minute) == \
               (dt2.year, dt2.month, dt2.day, dt2.hour, dt2.minute)
    elif unit == 'second':
        return (dt1.year, dt1.month, dt1.day, dt1.hour, dt1.minute, dt1.second) == \
               (dt2.year, dt2.month, dt2.day, dt2.hour, dt2.minute, dt2.second)
    else:
        return False


def format_date_range(
    start_date: Timestamp,
    end_date: Timestamp,
    initial: bool = False
) -> str:
    """
    Format a date range as a string.
    
    Args:
        start_date: The start date
        end_date: The end date
        initial: If True, always show full range format
        
    Returns:
        str: Formatted date range or 'Invalid date' if invalid
    """
    start_dt = to_datetime(start_date)
    end_dt = to_datetime(end_date)
    
    if None in (start_dt, end_dt) or start_dt > end_dt:
        return 'Invalid date'
    
    # Default full range format
    label = f"{format_date(start_dt)} - {format_date(end_dt)}"
    
    if initial:
        return label
    
    # Check if dates are in the same year/month/day
    same_year = is_same(start_dt, end_dt, 'year')
    same_month = is_same(start_dt, end_dt, 'month')
    same_day = is_same(start_dt, end_dt, 'day')
    
    if same_year and not same_month:
        # Same year, different months: "25 Apr - 26 May 2022"
        label = f"{start_dt.strftime('%d %b')} - {end_dt.strftime('%d %b %Y')}"
    elif same_year and same_month and not same_day:
        # Same year and month, different days: "25 - 26 Apr 2022"
        label = f"{start_dt.strftime('%d')} - {end_dt.strftime('%d %b %Y')}"
    elif same_day:
        # Same day: just show one date: "26 Apr 2022"
        label = format_date(end_dt)
    
    return label


def add_time(duration: DurationDict) -> datetime.datetime:
    """
    Add a duration to the current time.
    
    Args:
        duration: Dictionary with duration components
                 (years, months, days, hours, minutes, seconds, microseconds)
        
    Returns:
        datetime.datetime: Current time plus the specified duration
    """
    now = datetime.datetime.now(tz.tzlocal())
    delta = relativedelta(
        years=duration.get('years', 0),
        months=duration.get('months', 0),
        days=duration.get('days', 0),
        hours=duration.get('hours', 0),
        minutes=duration.get('minutes', 0),
        seconds=duration.get('seconds', 0),
        microseconds=duration.get('microseconds', 0)
    )
    return now + delta


def subtract_time(duration: DurationDict) -> datetime.datetime:
    """
    Subtract a duration from the current time.
    
    Args:
        duration: Dictionary with duration components
                 (years, months, days, hours, minutes, seconds, microseconds)
        
    Returns:
        datetime.datetime: Current time minus the specified duration
    """
    now = datetime.datetime.now(tz.tzlocal())
    delta = relativedelta(
        years=duration.get('years', 0),
        months=duration.get('months', 0),
        days=duration.get('days', 0),
        hours=duration.get('hours', 0),
        minutes=duration.get('minutes', 0),
        seconds=duration.get('seconds', 0),
        microseconds=duration.get('microseconds', 0)
    )
    return now - delta


def calculate_duration(start_time: Timestamp, end_time: Optional[Timestamp] = None) -> float:
    """
    Calculate the duration between two timestamps in seconds.
    If end_time is not provided, the current time is used.
    
    Args:
        start_time: The start timestamp
        end_time: The end timestamp (optional, defaults to current time)
        
    Returns:
        float: Duration in seconds
    """
    start_dt = to_datetime(start_time)
    if start_dt is None:
        return 0.0
    
    if end_time is None:
        end_dt = datetime.datetime.now(tz.tzlocal())
    else:
        end_dt = to_datetime(end_time)
        if end_dt is None:
            return 0.0
    
    # Ensure both datetimes have timezone information
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz.UTC)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=tz.UTC)
    
    return (end_dt - start_dt).total_seconds()


def calculate_processing_time(start_time: Timestamp, end_time: Optional[Timestamp] = None) -> Dict[str, Any]:
    """
    Calculate processing time metrics between two timestamps.
    
    Args:
        start_time: The start timestamp
        end_time: The end timestamp (optional, defaults to current time)
        
    Returns:
        Dict: Dictionary containing processing time metrics
              (total_seconds, formatted_time, start_iso, end_iso)
    """
    start_dt = to_datetime(start_time)
    if start_dt is None:
        return {
            'total_seconds': 0.0,
            'formatted_time': '0s',
            'start_iso': 'Invalid date',
            'end_iso': 'Invalid date'
        }
    
    if end_time is None:
        end_dt = datetime.datetime.now(tz.tzlocal())
    else:
        end_dt = to_datetime(end_time)
        if end_dt is None:
            return {
                'total_seconds': 0.0,
                'formatted_time': '0s',
                'start_iso': format_iso8601(start_dt),
                'end_iso': 'Invalid date'
            }
    
    # Ensure both datetimes have timezone information
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz.UTC)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=tz.UTC)
    
    total_seconds = (end_dt - start_dt).total_seconds()
    
    # Format the duration in a human-readable way
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        formatted_time = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        formatted_time = f"{int(minutes)}m {int(seconds)}s"
    else:
        formatted_time = f"{seconds:.2f}s"
    
    return {
        'total_seconds': total_seconds,
        'formatted_time': formatted_time,
        'start_iso': format_iso8601(start_dt),
        'end_iso': format_iso8601(end_dt)
    }


def calculate_age(date: Timestamp) -> str:
    """
    Calculate the age (time ago) of a timestamp in a human-readable format.
    
    Args:
        date: The timestamp to calculate age for
        
    Returns:
        str: Human-readable age (e.g., "2 hours ago", "5 minutes ago")
    """
    dt = to_datetime(date)
    if dt is None:
        return 'Invalid date'
    
    # Ensure datetime has timezone information
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.UTC)
    
    now = datetime.datetime.now(dt.tzinfo)
    delta = now - dt
    
    # Calculate the time difference
    seconds = delta.total_seconds()
    
    if seconds < 60:
        return 'just now' if seconds < 10 else f"{int(seconds)} seconds ago"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)} minute{'s' if int(minutes) != 1 else ''} ago"
    
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)} hour{'s' if int(hours) != 1 else ''} ago"
    
    days = hours / 24
    if days < 7:
        return f"{int(days)} day{'s' if int(days) != 1 else ''} ago"
    
    weeks = days / 7
    if weeks < 4:
        return f"{int(weeks)} week{'s' if int(weeks) != 1 else ''} ago"
    
    months = days / 30.44  # Average days per month
    if months < 12:
        return f"{int(months)} month{'s' if int(months) != 1 else ''} ago"
    
    years = days / 365.25  # Account for leap years
    return f"{int(years)} year{'s' if int(years) != 1 else ''} ago"


def get_log_timestamp() -> str:
    """
    Get a formatted timestamp for logging purposes.
    
    Returns:
        str: Formatted timestamp for logs
    """
    return datetime.datetime.now().strftime(FORMAT_PATTERNS['log'])


def get_document_processing_metadata(start_time: Timestamp) -> Dict[str, str]:
    """
    Generate document processing metadata with timestamps.
    
    Args:
        start_time: The start timestamp of processing
        
    Returns:
        Dict: Dictionary containing processing metadata with timestamps
    """
    now = datetime.datetime.now(tz.tzlocal())
    start_dt = to_datetime(start_time)
    
    if start_dt is None:
        start_dt = now
    
    # Ensure datetime has timezone information
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz.tzlocal())
    
    processing_time = calculate_processing_time(start_dt, now)
    
    return {
        'processing_started': format_iso8601(start_dt),
        'processing_completed': format_iso8601(now),
        'processing_duration_seconds': str(processing_time['total_seconds']),
        'processing_duration_formatted': processing_time['formatted_time'],
        'timestamp': format_iso8601(now)
    }