package com.dollarfunding.mca.util;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.Date;

/**
 * Utility class for date and time operations in the MCA application.
 * Provides methods for formatting, parsing, comparison, and manipulation of dates and timestamps.
 * Ensures consistent date/time handling across the application with support for different formats and time zones.
 */
public final class DateTimeUtil {

    /**
     * Standard date/time format patterns
     */
    public static final class FormatPatterns {
        public static final String DATE_TIME = "dd MMM yyyy h:mm a"; // 17 Apr 2022 12:00 am
        public static final String DATE = "dd MMM yyyy"; // 17 Apr 2022
        public static final String TIME = "h:mm a"; // 12:00 am
        
        public static final class Split {
            public static final String DATE_TIME = "dd/MM/yyyy h:mm a"; // 17/04/2022 12:00 am
            public static final String DATE = "dd/MM/yyyy"; // 17/04/2022
        }
        
        public static final class ParamCase {
            public static final String DATE_TIME = "dd-MM-yyyy h:mm a"; // 17-04-2022 12:00 am
            public static final String DATE = "dd-MM-yyyy"; // 17-04-2022
        }
        
        public static final String ISO_DATE_TIME = "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"; // ISO-8601 format
    }
    
    /**
     * Default time zone for the application
     */
    public static final ZoneId DEFAULT_ZONE_ID = ZoneId.systemDefault();
    
    /**
     * Private constructor to prevent instantiation
     */
    private DateTimeUtil() {
        throw new IllegalStateException("Utility class");
    }
    
    /**
     * Formats a date/time object to a string using the default format pattern.
     * 
     * @param dateTime The date/time object to format
     * @return The formatted date/time string
     */
    public static String formatDateTime(LocalDateTime dateTime) {
        return formatDateTime(dateTime, FormatPatterns.DATE_TIME);
    }
    
    /**
     * Formats a date/time object to a string using the specified format pattern.
     * 
     * @param dateTime The date/time object to format
     * @param pattern The format pattern to use
     * @return The formatted date/time string
     */
    public static String formatDateTime(LocalDateTime dateTime, String pattern) {
        if (dateTime == null) {
            return "Invalid date";
        }
        return DateTimeFormatter.ofPattern(pattern).format(dateTime);
    }
    
    /**
     * Formats a date object to a string using the default date format pattern.
     * 
     * @param date The date object to format
     * @return The formatted date string
     */
    public static String formatDate(LocalDate date) {
        return formatDate(date, FormatPatterns.DATE);
    }
    
    /**
     * Formats a date object to a string using the specified format pattern.
     * 
     * @param date The date object to format
     * @param pattern The format pattern to use
     * @return The formatted date string
     */
    public static String formatDate(LocalDate date, String pattern) {
        if (date == null) {
            return "Invalid date";
        }
        return DateTimeFormatter.ofPattern(pattern).format(date);
    }
    
    /**
     * Formats a time object to a string using the default time format pattern.
     * 
     * @param time The time object to format
     * @return The formatted time string
     */
    public static String formatTime(LocalTime time) {
        return formatTime(time, FormatPatterns.TIME);
    }
    
    /**
     * Formats a time object to a string using the specified format pattern.
     * 
     * @param time The time object to format
     * @param pattern The format pattern to use
     * @return The formatted time string
     */
    public static String formatTime(LocalTime time, String pattern) {
        if (time == null) {
            return "Invalid time";
        }
        return DateTimeFormatter.ofPattern(pattern).format(time);
    }
    
    /**
     * Parses a date/time string to a LocalDateTime object using the default format pattern.
     * 
     * @param dateTimeStr The date/time string to parse
     * @return The parsed LocalDateTime object, or null if parsing fails
     */
    public static LocalDateTime parseDateTime(String dateTimeStr) {
        return parseDateTime(dateTimeStr, FormatPatterns.DATE_TIME);
    }
    
    /**
     * Parses a date/time string to a LocalDateTime object using the specified format pattern.
     * 
     * @param dateTimeStr The date/time string to parse
     * @param pattern The format pattern to use
     * @return The parsed LocalDateTime object, or null if parsing fails
     */
    public static LocalDateTime parseDateTime(String dateTimeStr, String pattern) {
        if (dateTimeStr == null || dateTimeStr.isEmpty()) {
            return null;
        }
        try {
            return LocalDateTime.parse(dateTimeStr, DateTimeFormatter.ofPattern(pattern));
        } catch (DateTimeParseException e) {
            return null;
        }
    }
    
    /**
     * Gets the current date/time.
     * 
     * @return The current LocalDateTime
     */
    public static LocalDateTime getCurrentDateTime() {
        return LocalDateTime.now();
    }
    
    /**
     * Gets the current date/time in the specified time zone.
     * 
     * @param zoneId The time zone ID
     * @return The current LocalDateTime in the specified time zone
     */
    public static LocalDateTime getCurrentDateTime(ZoneId zoneId) {
        return LocalDateTime.now(zoneId);
    }
    
    /**
     * Calculates the difference between two dates in days.
     * 
     * @param startDate The start date
     * @param endDate The end date
     * @return The difference in days, or -1 if either date is null
     */
    public static long calculateDateDifference(LocalDate startDate, LocalDate endDate) {
        if (startDate == null || endDate == null) {
            return -1;
        }
        return ChronoUnit.DAYS.between(startDate, endDate);
    }
    
    /**
     * Calculates the difference between two date/times in the specified unit.
     * 
     * @param startDateTime The start date/time
     * @param endDateTime The end date/time
     * @param unit The time unit to use for the calculation
     * @return The difference in the specified unit, or -1 if either date/time is null
     */
    public static long calculateDateTimeDifference(LocalDateTime startDateTime, LocalDateTime endDateTime, ChronoUnit unit) {
        if (startDateTime == null || endDateTime == null) {
            return -1;
        }
        return unit.between(startDateTime, endDateTime);
    }
    
    /**
     * Adds days to a date.
     * 
     * @param date The date to add days to
     * @param days The number of days to add
     * @return The new date with days added, or null if the input date is null
     */
    public static LocalDate addDaysToDate(LocalDate date, long days) {
        if (date == null) {
            return null;
        }
        return date.plusDays(days);
    }
    
    /**
     * Adds days to a date/time.
     * 
     * @param dateTime The date/time to add days to
     * @param days The number of days to add
     * @return The new date/time with days added, or null if the input date/time is null
     */
    public static LocalDateTime addDaysToDateTime(LocalDateTime dateTime, long days) {
        if (dateTime == null) {
            return null;
        }
        return dateTime.plusDays(days);
    }
    
    /**
     * Checks if a date is between two other dates (inclusive).
     * 
     * @param date The date to check
     * @param startDate The start date of the range
     * @param endDate The end date of the range
     * @return true if the date is between the start and end dates (inclusive), false otherwise
     */
    public static boolean isDateBetween(LocalDate date, LocalDate startDate, LocalDate endDate) {
        if (date == null || startDate == null || endDate == null) {
            return false;
        }
        return !date.isBefore(startDate) && !date.isAfter(endDate);
    }
    
    /**
     * Checks if a date/time is between two other date/times (inclusive).
     * 
     * @param dateTime The date/time to check
     * @param startDateTime The start date/time of the range
     * @param endDateTime The end date/time of the range
     * @return true if the date/time is between the start and end date/times (inclusive), false otherwise
     */
    public static boolean isDateTimeBetween(LocalDateTime dateTime, LocalDateTime startDateTime, LocalDateTime endDateTime) {
        if (dateTime == null || startDateTime == null || endDateTime == null) {
            return false;
        }
        return !dateTime.isBefore(startDateTime) && !dateTime.isAfter(endDateTime);
    }
    
    /**
     * Converts a date/time from one time zone to another.
     * 
     * @param dateTime The date/time to convert
     * @param fromZoneId The source time zone ID
     * @param toZoneId The target time zone ID
     * @return The converted date/time, or null if the input date/time is null
     */
    public static LocalDateTime convertTimeZone(LocalDateTime dateTime, ZoneId fromZoneId, ZoneId toZoneId) {
        if (dateTime == null) {
            return null;
        }
        ZonedDateTime zonedDateTime = dateTime.atZone(fromZoneId);
        ZonedDateTime convertedZonedDateTime = zonedDateTime.withZoneSameInstant(toZoneId);
        return convertedZonedDateTime.toLocalDateTime();
    }
    
    /**
     * Converts a java.util.Date to a LocalDateTime.
     * 
     * @param date The java.util.Date to convert
     * @return The converted LocalDateTime, or null if the input date is null
     */
    public static LocalDateTime toLocalDateTime(Date date) {
        if (date == null) {
            return null;
        }
        return LocalDateTime.ofInstant(date.toInstant(), DEFAULT_ZONE_ID);
    }
    
    /**
     * Converts a LocalDateTime to a java.util.Date.
     * 
     * @param dateTime The LocalDateTime to convert
     * @return The converted java.util.Date, or null if the input date/time is null
     */
    public static Date toDate(LocalDateTime dateTime) {
        if (dateTime == null) {
            return null;
        }
        return Date.from(dateTime.atZone(DEFAULT_ZONE_ID).toInstant());
    }
    
    /**
     * Gets the timestamp (milliseconds since epoch) for a date/time.
     * 
     * @param dateTime The date/time to get the timestamp for
     * @return The timestamp in milliseconds, or -1 if the input date/time is null
     */
    public static long getTimestamp(LocalDateTime dateTime) {
        if (dateTime == null) {
            return -1;
        }
        return dateTime.atZone(DEFAULT_ZONE_ID).toInstant().toEpochMilli();
    }
    
    /**
     * Creates a LocalDateTime from a timestamp (milliseconds since epoch).
     * 
     * @param timestamp The timestamp in milliseconds
     * @return The LocalDateTime corresponding to the timestamp
     */
    public static LocalDateTime fromTimestamp(long timestamp) {
        return LocalDateTime.ofInstant(Instant.ofEpochMilli(timestamp), DEFAULT_ZONE_ID);
    }
    
    /**
     * Checks if a date is after another date.
     * 
     * @param date The date to check
     * @param otherDate The date to compare against
     * @return true if the date is after the other date, false otherwise
     */
    public static boolean isDateAfter(LocalDate date, LocalDate otherDate) {
        if (date == null || otherDate == null) {
            return false;
        }
        return date.isAfter(otherDate);
    }
    
    /**
     * Checks if a date/time is after another date/time.
     * 
     * @param dateTime The date/time to check
     * @param otherDateTime The date/time to compare against
     * @return true if the date/time is after the other date/time, false otherwise
     */
    public static boolean isDateTimeAfter(LocalDateTime dateTime, LocalDateTime otherDateTime) {
        if (dateTime == null || otherDateTime == null) {
            return false;
        }
        return dateTime.isAfter(otherDateTime);
    }
    
    /**
     * Checks if two dates are on the same day.
     * 
     * @param date1 The first date
     * @param date2 The second date
     * @return true if the dates are on the same day, false otherwise
     */
    public static boolean isSameDay(LocalDate date1, LocalDate date2) {
        if (date1 == null || date2 == null) {
            return false;
        }
        return date1.isEqual(date2);
    }
    
    /**
     * Checks if two date/times are on the same day.
     * 
     * @param dateTime1 The first date/time
     * @param dateTime2 The second date/time
     * @return true if the date/times are on the same day, false otherwise
     */
    public static boolean isSameDay(LocalDateTime dateTime1, LocalDateTime dateTime2) {
        if (dateTime1 == null || dateTime2 == null) {
            return false;
        }
        return dateTime1.toLocalDate().isEqual(dateTime2.toLocalDate());
    }
    
    /**
     * Formats a date range in a human-readable format.
     * If dates are in the same day, returns only one date.
     * If dates are in the same month, returns "DD - DD MMM YYYY".
     * If dates are in different months but same year, returns "DD MMM - DD MMM YYYY".
     * Otherwise, returns "DD MMM YYYY - DD MMM YYYY".
     * 
     * @param startDate The start date
     * @param endDate The end date
     * @return The formatted date range string
     */
    public static String formatDateRange(LocalDate startDate, LocalDate endDate) {
        if (startDate == null || endDate == null || startDate.isAfter(endDate)) {
            return "Invalid date range";
        }
        
        if (isSameDay(startDate, endDate)) {
            return formatDate(endDate);
        }
        
        boolean sameYear = startDate.getYear() == endDate.getYear();
        boolean sameMonth = sameYear && startDate.getMonth() == endDate.getMonth();
        
        if (sameYear && !sameMonth) {
            return formatDate(startDate, "dd MMM") + " - " + formatDate(endDate);
        } else if (sameYear && sameMonth) {
            return formatDate(startDate, "dd") + " - " + formatDate(endDate);
        } else {
            return formatDate(startDate) + " - " + formatDate(endDate);
        }
    }
    
    /**
     * Gets the duration between two date/times in a human-readable format.
     * 
     * @param startDateTime The start date/time
     * @param endDateTime The end date/time
     * @return The formatted duration string
     */
    public static String formatDuration(LocalDateTime startDateTime, LocalDateTime endDateTime) {
        if (startDateTime == null || endDateTime == null) {
            return "Invalid duration";
        }
        
        Duration duration = Duration.between(startDateTime, endDateTime);
        long days = duration.toDays();
        long hours = duration.toHoursPart();
        long minutes = duration.toMinutesPart();
        long seconds = duration.toSecondsPart();
        
        StringBuilder sb = new StringBuilder();
        if (days > 0) {
            sb.append(days).append(days == 1 ? " day" : " days");
        }
        if (hours > 0) {
            if (sb.length() > 0) sb.append(", ");
            sb.append(hours).append(hours == 1 ? " hour" : " hours");
        }
        if (minutes > 0) {
            if (sb.length() > 0) sb.append(", ");
            sb.append(minutes).append(minutes == 1 ? " minute" : " minutes");
        }
        if (seconds > 0 || sb.length() == 0) {
            if (sb.length() > 0) sb.append(", ");
            sb.append(seconds).append(seconds == 1 ? " second" : " seconds");
        }
        
        return sb.toString();
    }
}