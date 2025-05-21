#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Time utilities for the Document Service.

This module provides functions for timestamp generation, date comparison,
duration calculation, and time formatting. It ensures consistent timestamp
handling across the Document Service for logs, message publishing, and document metadata.
"""

import datetime
import time
from typing import Optional, Union, Tuple, Any

# Try to use zoneinfo (Python 3.9+) for timezone handling
# Fall back to pytz for older Python versions
try:
    from zoneinfo import ZoneInfo
    USING_ZONEINFO = True
except ImportError:
    import pytz
    USING_ZONEINFO = False

# Constants
ISO_8601_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # ISO 8601 format with UTC timezone
ISO_8601_FORMAT_WITH_TZ = "%Y-%m-%dT%H:%M:%S.%f%z"  # ISO 8601 format with timezone
DEFAULT_TIMEZONE = "UTC"  # Default timezone for timestamp generation


def get_current_timestamp() -> datetime.datetime:
    """
    Get the current timestamp as a timezone-aware datetime object in UTC.
    
    Returns:
        datetime.datetime: Current UTC timestamp with timezone information
    """
    return datetime.datetime.now(datetime.timezone.utc)


def get_timestamp_str() -> str:
    """
    Get the current timestamp as an ISO 8601 formatted string in UTC.
    
    Returns:
        str: ISO 8601 formatted timestamp string
    """
    return get_current_timestamp().isoformat()


def get_timestamp_with_timezone(tz_name: str = DEFAULT_TIMEZONE) -> datetime.datetime:
    """
    Get the current timestamp with the specified timezone.
    
    Args:
        tz_name (str): Timezone name (e.g., 'America/New_York', 'Europe/London')
                       Defaults to UTC if not specified
    
    Returns:
        datetime.datetime: Current timestamp with specified timezone
    
    Raises:
        ValueError: If the timezone name is invalid
    """
    try:
        if USING_ZONEINFO:
            tz = ZoneInfo(tz_name)
        else:
            tz = pytz.timezone(tz_name)
        return datetime.datetime.now(tz)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {tz_name}") from e


def format_timestamp(dt: datetime.datetime, include_timezone: bool = True) -> str:
    """
    Format a datetime object as an ISO 8601 string.
    
    Args:
        dt (datetime.datetime): Datetime object to format
        include_timezone (bool): Whether to include timezone information
    
    Returns:
        str: ISO 8601 formatted timestamp string
    """
    if dt.tzinfo is None and include_timezone:
        # Make timezone-aware with UTC if it's naive
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    return dt.isoformat()


def parse_timestamp(timestamp_str: str) -> datetime.datetime:
    """
    Parse an ISO 8601 formatted timestamp string into a datetime object.
    
    Args:
        timestamp_str (str): ISO 8601 formatted timestamp string
    
    Returns:
        datetime.datetime: Parsed datetime object with timezone information
    
    Raises:
        ValueError: If the timestamp string is not in a valid ISO 8601 format
    """
    try:
        # Handle 'Z' timezone designator for UTC
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        
        return datetime.datetime.fromisoformat(timestamp_str)
    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 timestamp: {timestamp_str}") from e


def format_human_readable(dt: datetime.datetime) -> str:
    """
    Format a datetime object in a human-readable format.
    
    Args:
        dt (datetime.datetime): Datetime object to format
    
    Returns:
        str: Human-readable timestamp string (e.g., "2023-04-15 14:30:45")
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_same_day(dt1: datetime.datetime, dt2: datetime.datetime) -> bool:
    """
    Check if two datetime objects represent the same day.
    
    Args:
        dt1 (datetime.datetime): First datetime object
        dt2 (datetime.datetime): Second datetime object
    
    Returns:
        bool: True if both datetimes are on the same day, False otherwise
    """
    return (dt1.year == dt2.year and 
            dt1.month == dt2.month and 
            dt1.day == dt2.day)


def is_before(dt1: datetime.datetime, dt2: datetime.datetime) -> bool:
    """
    Check if the first datetime is before the second datetime.
    
    Args:
        dt1 (datetime.datetime): First datetime object
        dt2 (datetime.datetime): Second datetime object
    
    Returns:
        bool: True if dt1 is before dt2, False otherwise
    """
    # Ensure both datetimes are timezone-aware for comparison
    if dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=datetime.timezone.utc)
    if dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=datetime.timezone.utc)
    
    return dt1 < dt2


def is_after(dt1: datetime.datetime, dt2: datetime.datetime) -> bool:
    """
    Check if the first datetime is after the second datetime.
    
    Args:
        dt1 (datetime.datetime): First datetime object
        dt2 (datetime.datetime): Second datetime object
    
    Returns:
        bool: True if dt1 is after dt2, False otherwise
    """
    # Ensure both datetimes are timezone-aware for comparison
    if dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=datetime.timezone.utc)
    if dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=datetime.timezone.utc)
    
    return dt1 > dt2


def is_between(dt: datetime.datetime, start: datetime.datetime, end: datetime.datetime) -> bool:
    """
    Check if a datetime is between two other datetimes (inclusive).
    
    Args:
        dt (datetime.datetime): Datetime to check
        start (datetime.datetime): Start datetime
        end (datetime.datetime): End datetime
    
    Returns:
        bool: True if dt is between start and end (inclusive), False otherwise
    """
    # Ensure all datetimes are timezone-aware for comparison
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.timezone.utc)
    
    return start <= dt <= end


def calculate_duration(start: datetime.datetime, end: datetime.datetime) -> datetime.timedelta:
    """
    Calculate the duration between two datetime objects.
    
    Args:
        start (datetime.datetime): Start datetime
        end (datetime.datetime): End datetime
    
    Returns:
        datetime.timedelta: Duration between start and end
    """
    # Ensure both datetimes are timezone-aware for calculation
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.timezone.utc)
    
    return end - start


def format_duration(td: datetime.timedelta) -> str:
    """
    Format a timedelta object as a human-readable string.
    
    Args:
        td (datetime.timedelta): Timedelta object to format
    
    Returns:
        str: Human-readable duration string (e.g., "2 days, 3 hours, 45 minutes")
    """
    seconds = td.total_seconds()
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{int(days)} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{int(hours)} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{int(minutes)} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds:.2f} second{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts)


def format_duration_short(td: datetime.timedelta) -> str:
    """
    Format a timedelta object as a short human-readable string.
    
    Args:
        td (datetime.timedelta): Timedelta object to format
    
    Returns:
        str: Short human-readable duration string (e.g., "2d 3h 45m")
    """
    seconds = td.total_seconds()
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{int(days)}d")
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    if seconds > 0 or not parts:
        parts.append(f"{int(seconds)}s")
    
    return " ".join(parts)


def calculate_age(dt: datetime.datetime) -> datetime.timedelta:
    """
    Calculate the age of a datetime (time elapsed since the datetime until now).
    
    Args:
        dt (datetime.datetime): Datetime to calculate age from
    
    Returns:
        datetime.timedelta: Age as a timedelta object
    """
    now = get_current_timestamp()
    
    # Ensure dt is timezone-aware for calculation
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    return now - dt


def format_age(dt: datetime.datetime, short: bool = False) -> str:
    """
    Format the age of a datetime as a human-readable string.
    
    Args:
        dt (datetime.datetime): Datetime to calculate age from
        short (bool): Whether to use short format
    
    Returns:
        str: Human-readable age string
    """
    age = calculate_age(dt)
    
    if short:
        return format_duration_short(age)
    else:
        return format_duration(age)


def calculate_processing_time(start_time: float) -> float:
    """
    Calculate the processing time from a start time (in seconds).
    
    Args:
        start_time (float): Start time as returned by time.time()
    
    Returns:
        float: Processing time in seconds
    """
    return time.time() - start_time


def format_processing_time(processing_time: float) -> str:
    """
    Format a processing time as a human-readable string.
    
    Args:
        processing_time (float): Processing time in seconds
    
    Returns:
        str: Human-readable processing time string
    """
    if processing_time < 0.001:
        return f"{processing_time * 1000000:.2f} μs"  # microseconds
    elif processing_time < 1.0:
        return f"{processing_time * 1000:.2f} ms"  # milliseconds
    else:
        return f"{processing_time:.2f} s"  # seconds


def get_timestamp_for_filename() -> str:
    """
    Get a timestamp string suitable for use in filenames.
    
    Returns:
        str: Timestamp string for filenames (e.g., "20230415_143045")
    """
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def convert_timezone(dt: datetime.datetime, target_tz: str) -> datetime.datetime:
    """
    Convert a datetime object to a different timezone.
    
    Args:
        dt (datetime.datetime): Datetime object to convert
        target_tz (str): Target timezone name
    
    Returns:
        datetime.datetime: Datetime object in the target timezone
    
    Raises:
        ValueError: If the target timezone is invalid
    """
    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    try:
        if USING_ZONEINFO:
            target_timezone = ZoneInfo(target_tz)
        else:
            target_timezone = pytz.timezone(target_tz)
        
        return dt.astimezone(target_timezone)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {target_tz}") from e


def get_timezone_offset(tz_name: str = DEFAULT_TIMEZONE) -> str:
    """
    Get the offset of a timezone from UTC.
    
    Args:
        tz_name (str): Timezone name
    
    Returns:
        str: Timezone offset string (e.g., "+05:00", "-08:00")
    
    Raises:
        ValueError: If the timezone name is invalid
    """
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if USING_ZONEINFO:
            tz = ZoneInfo(tz_name)
        else:
            tz = pytz.timezone(tz_name)
        
        offset = now.astimezone(tz).strftime('%z')
        # Format offset as +HH:MM or -HH:MM
        return f"{offset[:3]}:{offset[3:]}"
    except Exception as e:
        raise ValueError(f"Invalid timezone: {tz_name}") from e


def add_timezone_info(dt: datetime.datetime, tz_name: str = DEFAULT_TIMEZONE) -> datetime.datetime:
    """
    Add timezone information to a naive datetime object.
    
    Args:
        dt (datetime.datetime): Naive datetime object
        tz_name (str): Timezone name
    
    Returns:
        datetime.datetime: Timezone-aware datetime object
    
    Raises:
        ValueError: If the timezone name is invalid or if dt already has timezone info
    """
    if dt.tzinfo is not None:
        raise ValueError("Datetime object already has timezone information")
    
    try:
        if USING_ZONEINFO:
            tz = ZoneInfo(tz_name)
        else:
            tz = pytz.timezone(tz_name)
            return tz.localize(dt)
        
        return dt.replace(tzinfo=tz)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {tz_name}") from e


def timestamp_to_unix(dt: datetime.datetime) -> float:
    """
    Convert a datetime object to a Unix timestamp (seconds since epoch).
    
    Args:
        dt (datetime.datetime): Datetime object to convert
    
    Returns:
        float: Unix timestamp
    """
    # Ensure dt is timezone-aware for calculation
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    return dt.timestamp()


def unix_to_timestamp(unix_time: float) -> datetime.datetime:
    """
    Convert a Unix timestamp to a datetime object.
    
    Args:
        unix_time (float): Unix timestamp (seconds since epoch)
    
    Returns:
        datetime.datetime: Timezone-aware datetime object in UTC
    """
    return datetime.datetime.fromtimestamp(unix_time, tz=datetime.timezone.utc)


def get_document_processing_start_time() -> float:
    """
    Get a start time for document processing.
    
    Returns:
        float: Start time as returned by time.time()
    """
    return time.time()


def calculate_document_processing_time(start_time: float) -> Tuple[float, str]:
    """
    Calculate the document processing time and format it.
    
    Args:
        start_time (float): Start time as returned by get_document_processing_start_time()
    
    Returns:
        Tuple[float, str]: Processing time in seconds and formatted string
    """
    processing_time = calculate_processing_time(start_time)
    formatted_time = format_processing_time(processing_time)
    return processing_time, formatted_time


def format_timestamp_for_message(dt: Optional[datetime.datetime] = None) -> str:
    """
    Format a timestamp for inclusion in a message payload.
    
    Args:
        dt (Optional[datetime.datetime]): Datetime object to format, or None for current time
    
    Returns:
        str: ISO 8601 formatted timestamp string with UTC timezone
    """
    if dt is None:
        dt = get_current_timestamp()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    return dt.isoformat()


def format_document_metadata_timestamp(dt: Optional[datetime.datetime] = None) -> str:
    """
    Format a timestamp for document metadata.
    
    Args:
        dt (Optional[datetime.datetime]): Datetime object to format, or None for current time
    
    Returns:
        str: ISO 8601 formatted timestamp string with UTC timezone
    """
    return format_timestamp_for_message(dt)


def format_log_timestamp(dt: Optional[datetime.datetime] = None) -> str:
    """
    Format a timestamp for log entries.
    
    Args:
        dt (Optional[datetime.datetime]): Datetime object to format, or None for current time
    
    Returns:
        str: ISO 8601 formatted timestamp string with UTC timezone
    """
    if dt is None:
        dt = get_current_timestamp()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compare_document_timestamps(doc1_timestamp: Union[str, datetime.datetime], 
                               doc2_timestamp: Union[str, datetime.datetime]) -> int:
    """
    Compare two document timestamps and determine which is more recent.
    
    Args:
        doc1_timestamp (Union[str, datetime.datetime]): First document timestamp
        doc2_timestamp (Union[str, datetime.datetime]): Second document timestamp
    
    Returns:
        int: -1 if doc1 is older, 0 if same time, 1 if doc1 is newer
    """
    # Convert string timestamps to datetime objects if needed
    if isinstance(doc1_timestamp, str):
        doc1_timestamp = parse_timestamp(doc1_timestamp)
    if isinstance(doc2_timestamp, str):
        doc2_timestamp = parse_timestamp(doc2_timestamp)
    
    # Ensure both timestamps are timezone-aware
    if doc1_timestamp.tzinfo is None:
        doc1_timestamp = doc1_timestamp.replace(tzinfo=datetime.timezone.utc)
    if doc2_timestamp.tzinfo is None:
        doc2_timestamp = doc2_timestamp.replace(tzinfo=datetime.timezone.utc)
    
    if doc1_timestamp < doc2_timestamp:
        return -1
    elif doc1_timestamp > doc2_timestamp:
        return 1
    else:
        return 0


def get_message_timestamp() -> dict:
    """
    Get a timestamp dictionary for inclusion in message payloads.
    
    Returns:
        dict: Dictionary with timestamp information
    """
    now = get_current_timestamp()
    return {
        "timestamp": format_timestamp_for_message(now),
        "unix_timestamp": timestamp_to_unix(now),
        "timezone": "UTC"
    }


def validate_timestamp_format(timestamp_str: str) -> bool:
    """
    Validate that a string is in a valid ISO 8601 timestamp format.
    
    Args:
        timestamp_str (str): Timestamp string to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        parse_timestamp(timestamp_str)
        return True
    except ValueError:
        return False


def get_document_age_category(created_timestamp: Union[str, datetime.datetime]) -> str:
    """
    Categorize a document based on its age.
    
    Args:
        created_timestamp (Union[str, datetime.datetime]): Document creation timestamp
    
    Returns:
        str: Age category ("new", "recent", "old", "archived")
    """
    # Convert string timestamp to datetime object if needed
    if isinstance(created_timestamp, str):
        created_timestamp = parse_timestamp(created_timestamp)
    
    # Ensure timestamp is timezone-aware
    if created_timestamp.tzinfo is None:
        created_timestamp = created_timestamp.replace(tzinfo=datetime.timezone.utc)
    
    age = calculate_age(created_timestamp)
    
    if age.days < 1:  # Less than 1 day old
        return "new"
    elif age.days < 7:  # Less than 1 week old
        return "recent"
    elif age.days < 30:  # Less than 1 month old
        return "old"
    else:  # 1 month or older
        return "archived"


def get_processing_deadline(received_timestamp: Union[str, datetime.datetime], 
                           processing_sla_minutes: int = 5) -> datetime.datetime:
    """
    Calculate the processing deadline for a document based on SLA.
    
    Args:
        received_timestamp (Union[str, datetime.datetime]): When the document was received
        processing_sla_minutes (int): SLA in minutes (default: 5 minutes)
    
    Returns:
        datetime.datetime: Deadline timestamp
    """
    # Convert string timestamp to datetime object if needed
    if isinstance(received_timestamp, str):
        received_timestamp = parse_timestamp(received_timestamp)
    
    # Ensure timestamp is timezone-aware
    if received_timestamp.tzinfo is None:
        received_timestamp = received_timestamp.replace(tzinfo=datetime.timezone.utc)
    
    return received_timestamp + datetime.timedelta(minutes=processing_sla_minutes)


def is_processing_overdue(received_timestamp: Union[str, datetime.datetime],
                         processing_sla_minutes: int = 5) -> bool:
    """
    Check if document processing is overdue based on SLA.
    
    Args:
        received_timestamp (Union[str, datetime.datetime]): When the document was received
        processing_sla_minutes (int): SLA in minutes (default: 5 minutes)
    
    Returns:
        bool: True if processing is overdue, False otherwise
    """
    deadline = get_processing_deadline(received_timestamp, processing_sla_minutes)
    now = get_current_timestamp()
    
    return now > deadline


def format_time_remaining(deadline: datetime.datetime) -> str:
    """
    Format the time remaining until a deadline.
    
    Args:
        deadline (datetime.datetime): Deadline timestamp
    
    Returns:
        str: Formatted time remaining string
    """
    now = get_current_timestamp()
    
    # Ensure deadline is timezone-aware
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=datetime.timezone.utc)
    
    if now > deadline:
        return "Overdue"
    
    remaining = deadline - now
    return format_duration(remaining)


# Main section for testing (will not be executed when imported)
if __name__ == "__main__":
    # Test timestamp generation
    print(f"Current timestamp: {get_current_timestamp()}")
    print(f"Current timestamp string: {get_timestamp_str()}")
    print(f"Timestamp with timezone (US/Eastern): {get_timestamp_with_timezone('US/Eastern')}")
    
    # Test formatting
    now = get_current_timestamp()
    print(f"Formatted timestamp: {format_timestamp(now)}")
    print(f"Human-readable timestamp: {format_human_readable(now)}")
    
    # Test duration calculation
    start = now - datetime.timedelta(hours=2, minutes=30)
    duration = calculate_duration(start, now)
    print(f"Duration: {duration}")
    print(f"Formatted duration: {format_duration(duration)}")
    print(f"Short formatted duration: {format_duration_short(duration)}")
    
    # Test document age
    doc_timestamp = now - datetime.timedelta(days=3)
    print(f"Document age: {format_age(doc_timestamp)}")
    print(f"Document age category: {get_document_age_category(doc_timestamp)}")
    
    # Test processing time
    start_time = get_document_processing_start_time()
    time.sleep(0.1)  # Simulate processing
    proc_time, formatted_proc_time = calculate_document_processing_time(start_time)
    print(f"Processing time: {proc_time} seconds ({formatted_proc_time})")
    
    # Test message timestamp
    print(f"Message timestamp: {get_message_timestamp()}")
    
    # Test processing deadline
    received = now - datetime.timedelta(minutes=4)
    deadline = get_processing_deadline(received)
    print(f"Processing deadline: {deadline}")
    print(f"Is processing overdue: {is_processing_overdue(received)}")
    print(f"Time remaining: {format_time_remaining(deadline)}")