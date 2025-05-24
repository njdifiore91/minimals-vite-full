package com.dollarfunding.mca.util;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.ChronoUnit;
import java.util.Date;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the DateTimeUtil class.
 * Tests date/time formatting, parsing, comparison, and manipulation operations.
 */
@DisplayName("DateTimeUtil Tests")
public class DateTimeUtilTest {

    @Test
    @DisplayName("Test formatDateTime with default pattern")
    public void testFormatDateTime() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        
        // When
        String formattedDateTime = DateTimeUtil.formatDateTime(dateTime);
        
        // Then
        assertEquals("17 Apr 2022 12:00 PM", formattedDateTime);
    }
    
    @Test
    @DisplayName("Test formatDateTime with custom pattern")
    public void testFormatDateTimeWithCustomPattern() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        String pattern = "yyyy-MM-dd HH:mm";
        
        // When
        String formattedDateTime = DateTimeUtil.formatDateTime(dateTime, pattern);
        
        // Then
        assertEquals("2022-04-17 12:00", formattedDateTime);
    }
    
    @Test
    @DisplayName("Test formatDateTime with null input")
    public void testFormatDateTimeWithNullInput() {
        // When
        String formattedDateTime = DateTimeUtil.formatDateTime(null);
        
        // Then
        assertEquals("Invalid date", formattedDateTime);
    }
    
    @Test
    @DisplayName("Test formatDate with default pattern")
    public void testFormatDate() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 17);
        
        // When
        String formattedDate = DateTimeUtil.formatDate(date);
        
        // Then
        assertEquals("17 Apr 2022", formattedDate);
    }
    
    @Test
    @DisplayName("Test formatDate with custom pattern")
    public void testFormatDateWithCustomPattern() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 17);
        String pattern = "yyyy-MM-dd";
        
        // When
        String formattedDate = DateTimeUtil.formatDate(date, pattern);
        
        // Then
        assertEquals("2022-04-17", formattedDate);
    }
    
    @Test
    @DisplayName("Test formatDate with null input")
    public void testFormatDateWithNullInput() {
        // When
        String formattedDate = DateTimeUtil.formatDate(null);
        
        // Then
        assertEquals("Invalid date", formattedDate);
    }
    
    @Test
    @DisplayName("Test formatTime with default pattern")
    public void testFormatTime() {
        // Given
        LocalTime time = LocalTime.of(12, 0);
        
        // When
        String formattedTime = DateTimeUtil.formatTime(time);
        
        // Then
        assertEquals("12:00 PM", formattedTime);
    }
    
    @Test
    @DisplayName("Test formatTime with custom pattern")
    public void testFormatTimeWithCustomPattern() {
        // Given
        LocalTime time = LocalTime.of(12, 0);
        String pattern = "HH:mm:ss";
        
        // When
        String formattedTime = DateTimeUtil.formatTime(time, pattern);
        
        // Then
        assertEquals("12:00:00", formattedTime);
    }
    
    @Test
    @DisplayName("Test formatTime with null input")
    public void testFormatTimeWithNullInput() {
        // When
        String formattedTime = DateTimeUtil.formatTime(null);
        
        // Then
        assertEquals("Invalid time", formattedTime);
    }
    
    @Test
    @DisplayName("Test parseDateTime with default pattern")
    public void testParseDateTime() {
        // Given
        String dateTimeStr = "17 Apr 2022 12:00 PM";
        
        // When
        LocalDateTime dateTime = DateTimeUtil.parseDateTime(dateTimeStr);
        
        // Then
        assertNotNull(dateTime);
        assertEquals(2022, dateTime.getYear());
        assertEquals(4, dateTime.getMonthValue());
        assertEquals(17, dateTime.getDayOfMonth());
        assertEquals(12, dateTime.getHour());
        assertEquals(0, dateTime.getMinute());
    }
    
    @Test
    @DisplayName("Test parseDateTime with custom pattern")
    public void testParseDateTimeWithCustomPattern() {
        // Given
        String dateTimeStr = "2022-04-17 12:00";
        String pattern = "yyyy-MM-dd HH:mm";
        
        // When
        LocalDateTime dateTime = DateTimeUtil.parseDateTime(dateTimeStr, pattern);
        
        // Then
        assertNotNull(dateTime);
        assertEquals(2022, dateTime.getYear());
        assertEquals(4, dateTime.getMonthValue());
        assertEquals(17, dateTime.getDayOfMonth());
        assertEquals(12, dateTime.getHour());
        assertEquals(0, dateTime.getMinute());
    }
    
    @Test
    @DisplayName("Test parseDateTime with null input")
    public void testParseDateTimeWithNullInput() {
        // When
        LocalDateTime dateTime = DateTimeUtil.parseDateTime(null);
        
        // Then
        assertNull(dateTime);
    }
    
    @Test
    @DisplayName("Test parseDateTime with empty string")
    public void testParseDateTimeWithEmptyString() {
        // When
        LocalDateTime dateTime = DateTimeUtil.parseDateTime("");
        
        // Then
        assertNull(dateTime);
    }
    
    @Test
    @DisplayName("Test parseDateTime with invalid format")
    public void testParseDateTimeWithInvalidFormat() {
        // Given
        String dateTimeStr = "invalid-date-format";
        
        // When
        LocalDateTime dateTime = DateTimeUtil.parseDateTime(dateTimeStr);
        
        // Then
        assertNull(dateTime);
    }
    
    @Test
    @DisplayName("Test getCurrentDateTime returns current time")
    public void testGetCurrentDateTime() {
        // When
        LocalDateTime now = DateTimeUtil.getCurrentDateTime();
        LocalDateTime systemNow = LocalDateTime.now();
        
        // Then
        assertNotNull(now);
        // Check that the time difference is less than 1 second
        long diffInSeconds = ChronoUnit.SECONDS.between(now, systemNow);
        assertTrue(Math.abs(diffInSeconds) < 1, "Time difference should be less than 1 second");
    }
    
    @Test
    @DisplayName("Test getCurrentDateTime with specific time zone")
    public void testGetCurrentDateTimeWithTimeZone() {
        // Given
        ZoneId zoneId = ZoneId.of("UTC");
        
        // When
        LocalDateTime dateTimeInZone = DateTimeUtil.getCurrentDateTime(zoneId);
        LocalDateTime systemNowInZone = LocalDateTime.now(zoneId);
        
        // Then
        assertNotNull(dateTimeInZone);
        // Check that the time difference is less than 1 second
        long diffInSeconds = ChronoUnit.SECONDS.between(dateTimeInZone, systemNowInZone);
        assertTrue(Math.abs(diffInSeconds) < 1, "Time difference should be less than 1 second");
    }
    
    @Test
    @DisplayName("Test calculateDateDifference with valid dates")
    public void testCalculateDateDifference() {
        // Given
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        long daysDifference = DateTimeUtil.calculateDateDifference(startDate, endDate);
        
        // Then
        assertEquals(10, daysDifference);
    }
    
    @Test
    @DisplayName("Test calculateDateDifference with null start date")
    public void testCalculateDateDifferenceWithNullStartDate() {
        // Given
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        long daysDifference = DateTimeUtil.calculateDateDifference(null, endDate);
        
        // Then
        assertEquals(-1, daysDifference);
    }
    
    @Test
    @DisplayName("Test calculateDateDifference with null end date")
    public void testCalculateDateDifferenceWithNullEndDate() {
        // Given
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        
        // When
        long daysDifference = DateTimeUtil.calculateDateDifference(startDate, null);
        
        // Then
        assertEquals(-1, daysDifference);
    }
    
    @Test
    @DisplayName("Test calculateDateTimeDifference with valid date times")
    public void testCalculateDateTimeDifference() {
        // Given
        LocalDateTime startDateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        LocalDateTime endDateTime = LocalDateTime.of(2022, 4, 17, 14, 30);
        
        // When
        long hoursDifference = DateTimeUtil.calculateDateTimeDifference(startDateTime, endDateTime, ChronoUnit.HOURS);
        long minutesDifference = DateTimeUtil.calculateDateTimeDifference(startDateTime, endDateTime, ChronoUnit.MINUTES);
        
        // Then
        assertEquals(2, hoursDifference);
        assertEquals(150, minutesDifference);
    }
    
    @Test
    @DisplayName("Test calculateDateTimeDifference with null inputs")
    public void testCalculateDateTimeDifferenceWithNullInputs() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        
        // When & Then
        assertEquals(-1, DateTimeUtil.calculateDateTimeDifference(null, dateTime, ChronoUnit.HOURS));
        assertEquals(-1, DateTimeUtil.calculateDateTimeDifference(dateTime, null, ChronoUnit.HOURS));
    }
    
    @Test
    @DisplayName("Test addDaysToDate with valid date")
    public void testAddDaysToDate() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 17);
        long daysToAdd = 10;
        
        // When
        LocalDate newDate = DateTimeUtil.addDaysToDate(date, daysToAdd);
        
        // Then
        assertNotNull(newDate);
        assertEquals(LocalDate.of(2022, 4, 27), newDate);
    }
    
    @Test
    @DisplayName("Test addDaysToDate with null date")
    public void testAddDaysToDateWithNullDate() {
        // When
        LocalDate newDate = DateTimeUtil.addDaysToDate(null, 10);
        
        // Then
        assertNull(newDate);
    }
    
    @Test
    @DisplayName("Test addDaysToDateTime with valid date time")
    public void testAddDaysToDateTime() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        long daysToAdd = 10;
        
        // When
        LocalDateTime newDateTime = DateTimeUtil.addDaysToDateTime(dateTime, daysToAdd);
        
        // Then
        assertNotNull(newDateTime);
        assertEquals(LocalDateTime.of(2022, 4, 27, 12, 0), newDateTime);
    }
    
    @Test
    @DisplayName("Test addDaysToDateTime with null date time")
    public void testAddDaysToDateTimeWithNullDateTime() {
        // When
        LocalDateTime newDateTime = DateTimeUtil.addDaysToDateTime(null, 10);
        
        // Then
        assertNull(newDateTime);
    }
    
    @Test
    @DisplayName("Test isDateBetween with date in range")
    public void testIsDateBetweenWithDateInRange() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 20);
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        boolean isInRange = DateTimeUtil.isDateBetween(date, startDate, endDate);
        
        // Then
        assertTrue(isInRange);
    }
    
    @Test
    @DisplayName("Test isDateBetween with date at start of range")
    public void testIsDateBetweenWithDateAtStartOfRange() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 17);
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        boolean isInRange = DateTimeUtil.isDateBetween(date, startDate, endDate);
        
        // Then
        assertTrue(isInRange);
    }
    
    @Test
    @DisplayName("Test isDateBetween with date at end of range")
    public void testIsDateBetweenWithDateAtEndOfRange() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 27);
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        boolean isInRange = DateTimeUtil.isDateBetween(date, startDate, endDate);
        
        // Then
        assertTrue(isInRange);
    }
    
    @Test
    @DisplayName("Test isDateBetween with date before range")
    public void testIsDateBetweenWithDateBeforeRange() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 16);
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        boolean isInRange = DateTimeUtil.isDateBetween(date, startDate, endDate);
        
        // Then
        assertFalse(isInRange);
    }
    
    @Test
    @DisplayName("Test isDateBetween with date after range")
    public void testIsDateBetweenWithDateAfterRange() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 28);
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        boolean isInRange = DateTimeUtil.isDateBetween(date, startDate, endDate);
        
        // Then
        assertFalse(isInRange);
    }
    
    @Test
    @DisplayName("Test isDateBetween with null inputs")
    public void testIsDateBetweenWithNullInputs() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 20);
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When & Then
        assertFalse(DateTimeUtil.isDateBetween(null, startDate, endDate));
        assertFalse(DateTimeUtil.isDateBetween(date, null, endDate));
        assertFalse(DateTimeUtil.isDateBetween(date, startDate, null));
    }
    
    @Test
    @DisplayName("Test isDateTimeBetween with date time in range")
    public void testIsDateTimeBetweenWithDateTimeInRange() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 20, 12, 0);
        LocalDateTime startDateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        LocalDateTime endDateTime = LocalDateTime.of(2022, 4, 27, 12, 0);
        
        // When
        boolean isInRange = DateTimeUtil.isDateTimeBetween(dateTime, startDateTime, endDateTime);
        
        // Then
        assertTrue(isInRange);
    }
    
    @Test
    @DisplayName("Test isDateTimeBetween with date time outside range")
    public void testIsDateTimeBetweenWithDateTimeOutsideRange() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 28, 12, 0);
        LocalDateTime startDateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        LocalDateTime endDateTime = LocalDateTime.of(2022, 4, 27, 12, 0);
        
        // When
        boolean isInRange = DateTimeUtil.isDateTimeBetween(dateTime, startDateTime, endDateTime);
        
        // Then
        assertFalse(isInRange);
    }
    
    @Test
    @DisplayName("Test isDateTimeBetween with null inputs")
    public void testIsDateTimeBetweenWithNullInputs() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 20, 12, 0);
        LocalDateTime startDateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        LocalDateTime endDateTime = LocalDateTime.of(2022, 4, 27, 12, 0);
        
        // When & Then
        assertFalse(DateTimeUtil.isDateTimeBetween(null, startDateTime, endDateTime));
        assertFalse(DateTimeUtil.isDateTimeBetween(dateTime, null, endDateTime));
        assertFalse(DateTimeUtil.isDateTimeBetween(dateTime, startDateTime, null));
    }
    
    @Test
    @DisplayName("Test convertTimeZone with valid inputs")
    public void testConvertTimeZone() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        ZoneId fromZoneId = ZoneId.of("UTC");
        ZoneId toZoneId = ZoneId.of("America/New_York");
        
        // When
        LocalDateTime convertedDateTime = DateTimeUtil.convertTimeZone(dateTime, fromZoneId, toZoneId);
        
        // Then
        assertNotNull(convertedDateTime);
        // UTC to New York is -4 or -5 hours depending on daylight saving time
        // April 17, 2022 is in DST, so it's UTC-4
        assertEquals(LocalDateTime.of(2022, 4, 17, 8, 0), convertedDateTime);
    }
    
    @Test
    @DisplayName("Test convertTimeZone with null date time")
    public void testConvertTimeZoneWithNullDateTime() {
        // Given
        ZoneId fromZoneId = ZoneId.of("UTC");
        ZoneId toZoneId = ZoneId.of("America/New_York");
        
        // When
        LocalDateTime convertedDateTime = DateTimeUtil.convertTimeZone(null, fromZoneId, toZoneId);
        
        // Then
        assertNull(convertedDateTime);
    }
    
    @Test
    @DisplayName("Test toLocalDateTime and toDate conversion")
    public void testDateConversion() {
        // Given
        LocalDateTime originalDateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        
        // When
        Date date = DateTimeUtil.toDate(originalDateTime);
        LocalDateTime convertedDateTime = DateTimeUtil.toLocalDateTime(date);
        
        // Then
        assertNotNull(date);
        assertNotNull(convertedDateTime);
        assertEquals(originalDateTime.getYear(), convertedDateTime.getYear());
        assertEquals(originalDateTime.getMonth(), convertedDateTime.getMonth());
        assertEquals(originalDateTime.getDayOfMonth(), convertedDateTime.getDayOfMonth());
        assertEquals(originalDateTime.getHour(), convertedDateTime.getHour());
        assertEquals(originalDateTime.getMinute(), convertedDateTime.getMinute());
    }
    
    @Test
    @DisplayName("Test toLocalDateTime and toDate with null inputs")
    public void testDateConversionWithNullInputs() {
        // When & Then
        assertNull(DateTimeUtil.toLocalDateTime(null));
        assertNull(DateTimeUtil.toDate(null));
    }
    
    @Test
    @DisplayName("Test getTimestamp and fromTimestamp")
    public void testTimestampConversion() {
        // Given
        LocalDateTime originalDateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        
        // When
        long timestamp = DateTimeUtil.getTimestamp(originalDateTime);
        LocalDateTime convertedDateTime = DateTimeUtil.fromTimestamp(timestamp);
        
        // Then
        assertTrue(timestamp > 0);
        assertNotNull(convertedDateTime);
        assertEquals(originalDateTime.getYear(), convertedDateTime.getYear());
        assertEquals(originalDateTime.getMonth(), convertedDateTime.getMonth());
        assertEquals(originalDateTime.getDayOfMonth(), convertedDateTime.getDayOfMonth());
        assertEquals(originalDateTime.getHour(), convertedDateTime.getHour());
        assertEquals(originalDateTime.getMinute(), convertedDateTime.getMinute());
    }
    
    @Test
    @DisplayName("Test getTimestamp with null input")
    public void testGetTimestampWithNullInput() {
        // When
        long timestamp = DateTimeUtil.getTimestamp(null);
        
        // Then
        assertEquals(-1, timestamp);
    }
    
    @Test
    @DisplayName("Test isDateAfter with date after other date")
    public void testIsDateAfter() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 27);
        LocalDate otherDate = LocalDate.of(2022, 4, 17);
        
        // When
        boolean isAfter = DateTimeUtil.isDateAfter(date, otherDate);
        
        // Then
        assertTrue(isAfter);
    }
    
    @Test
    @DisplayName("Test isDateAfter with date before other date")
    public void testIsDateAfterWithDateBeforeOtherDate() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 17);
        LocalDate otherDate = LocalDate.of(2022, 4, 27);
        
        // When
        boolean isAfter = DateTimeUtil.isDateAfter(date, otherDate);
        
        // Then
        assertFalse(isAfter);
    }
    
    @Test
    @DisplayName("Test isDateAfter with null inputs")
    public void testIsDateAfterWithNullInputs() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 27);
        
        // When & Then
        assertFalse(DateTimeUtil.isDateAfter(null, date));
        assertFalse(DateTimeUtil.isDateAfter(date, null));
    }
    
    @Test
    @DisplayName("Test isDateTimeAfter with date time after other date time")
    public void testIsDateTimeAfter() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 14, 0);
        LocalDateTime otherDateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        
        // When
        boolean isAfter = DateTimeUtil.isDateTimeAfter(dateTime, otherDateTime);
        
        // Then
        assertTrue(isAfter);
    }
    
    @Test
    @DisplayName("Test isDateTimeAfter with null inputs")
    public void testIsDateTimeAfterWithNullInputs() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 14, 0);
        
        // When & Then
        assertFalse(DateTimeUtil.isDateTimeAfter(null, dateTime));
        assertFalse(DateTimeUtil.isDateTimeAfter(dateTime, null));
    }
    
    @Test
    @DisplayName("Test isSameDay with LocalDate on same day")
    public void testIsSameDayWithLocalDate() {
        // Given
        LocalDate date1 = LocalDate.of(2022, 4, 17);
        LocalDate date2 = LocalDate.of(2022, 4, 17);
        
        // When
        boolean isSameDay = DateTimeUtil.isSameDay(date1, date2);
        
        // Then
        assertTrue(isSameDay);
    }
    
    @Test
    @DisplayName("Test isSameDay with LocalDate on different days")
    public void testIsSameDayWithLocalDateOnDifferentDays() {
        // Given
        LocalDate date1 = LocalDate.of(2022, 4, 17);
        LocalDate date2 = LocalDate.of(2022, 4, 18);
        
        // When
        boolean isSameDay = DateTimeUtil.isSameDay(date1, date2);
        
        // Then
        assertFalse(isSameDay);
    }
    
    @Test
    @DisplayName("Test isSameDay with LocalDateTime on same day")
    public void testIsSameDayWithLocalDateTime() {
        // Given
        LocalDateTime dateTime1 = LocalDateTime.of(2022, 4, 17, 12, 0);
        LocalDateTime dateTime2 = LocalDateTime.of(2022, 4, 17, 14, 0);
        
        // When
        boolean isSameDay = DateTimeUtil.isSameDay(dateTime1, dateTime2);
        
        // Then
        assertTrue(isSameDay);
    }
    
    @Test
    @DisplayName("Test isSameDay with LocalDateTime on different days")
    public void testIsSameDayWithLocalDateTimeOnDifferentDays() {
        // Given
        LocalDateTime dateTime1 = LocalDateTime.of(2022, 4, 17, 12, 0);
        LocalDateTime dateTime2 = LocalDateTime.of(2022, 4, 18, 12, 0);
        
        // When
        boolean isSameDay = DateTimeUtil.isSameDay(dateTime1, dateTime2);
        
        // Then
        assertFalse(isSameDay);
    }
    
    @Test
    @DisplayName("Test isSameDay with null inputs")
    public void testIsSameDayWithNullInputs() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 17);
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0);
        
        // When & Then
        assertFalse(DateTimeUtil.isSameDay((LocalDate) null, date));
        assertFalse(DateTimeUtil.isSameDay(date, null));
        assertFalse(DateTimeUtil.isSameDay((LocalDateTime) null, dateTime));
        assertFalse(DateTimeUtil.isSameDay(dateTime, null));
    }
    
    @Test
    @DisplayName("Test formatDateRange with dates in same day")
    public void testFormatDateRangeWithDatesInSameDay() {
        // Given
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 17);
        
        // When
        String formattedRange = DateTimeUtil.formatDateRange(startDate, endDate);
        
        // Then
        assertEquals("17 Apr 2022", formattedRange);
    }
    
    @Test
    @DisplayName("Test formatDateRange with dates in same month")
    public void testFormatDateRangeWithDatesInSameMonth() {
        // Given
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 4, 27);
        
        // When
        String formattedRange = DateTimeUtil.formatDateRange(startDate, endDate);
        
        // Then
        assertEquals("17 - 27 Apr 2022", formattedRange);
    }
    
    @Test
    @DisplayName("Test formatDateRange with dates in same year but different months")
    public void testFormatDateRangeWithDatesInSameYearDifferentMonths() {
        // Given
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2022, 5, 17);
        
        // When
        String formattedRange = DateTimeUtil.formatDateRange(startDate, endDate);
        
        // Then
        assertEquals("17 Apr - 17 May 2022", formattedRange);
    }
    
    @Test
    @DisplayName("Test formatDateRange with dates in different years")
    public void testFormatDateRangeWithDatesInDifferentYears() {
        // Given
        LocalDate startDate = LocalDate.of(2022, 4, 17);
        LocalDate endDate = LocalDate.of(2023, 4, 17);
        
        // When
        String formattedRange = DateTimeUtil.formatDateRange(startDate, endDate);
        
        // Then
        assertEquals("17 Apr 2022 - 17 Apr 2023", formattedRange);
    }
    
    @Test
    @DisplayName("Test formatDateRange with null inputs")
    public void testFormatDateRangeWithNullInputs() {
        // Given
        LocalDate date = LocalDate.of(2022, 4, 17);
        
        // When & Then
        assertEquals("Invalid date range", DateTimeUtil.formatDateRange(null, date));
        assertEquals("Invalid date range", DateTimeUtil.formatDateRange(date, null));
    }
    
    @Test
    @DisplayName("Test formatDateRange with invalid range")
    public void testFormatDateRangeWithInvalidRange() {
        // Given
        LocalDate startDate = LocalDate.of(2022, 4, 27);
        LocalDate endDate = LocalDate.of(2022, 4, 17);
        
        // When
        String formattedRange = DateTimeUtil.formatDateRange(startDate, endDate);
        
        // Then
        assertEquals("Invalid date range", formattedRange);
    }
    
    @Test
    @DisplayName("Test formatDuration with valid inputs")
    public void testFormatDuration() {
        // Given
        LocalDateTime startDateTime = LocalDateTime.of(2022, 4, 17, 12, 0, 0);
        LocalDateTime endDateTime = LocalDateTime.of(2022, 4, 18, 14, 30, 45);
        
        // When
        String formattedDuration = DateTimeUtil.formatDuration(startDateTime, endDateTime);
        
        // Then
        assertEquals("1 day, 2 hours, 30 minutes, 45 seconds", formattedDuration);
    }
    
    @Test
    @DisplayName("Test formatDuration with small duration")
    public void testFormatDurationWithSmallDuration() {
        // Given
        LocalDateTime startDateTime = LocalDateTime.of(2022, 4, 17, 12, 0, 0);
        LocalDateTime endDateTime = LocalDateTime.of(2022, 4, 17, 12, 0, 45);
        
        // When
        String formattedDuration = DateTimeUtil.formatDuration(startDateTime, endDateTime);
        
        // Then
        assertEquals("45 seconds", formattedDuration);
    }
    
    @Test
    @DisplayName("Test formatDuration with zero duration")
    public void testFormatDurationWithZeroDuration() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0, 0);
        
        // When
        String formattedDuration = DateTimeUtil.formatDuration(dateTime, dateTime);
        
        // Then
        assertEquals("0 seconds", formattedDuration);
    }
    
    @Test
    @DisplayName("Test formatDuration with null inputs")
    public void testFormatDurationWithNullInputs() {
        // Given
        LocalDateTime dateTime = LocalDateTime.of(2022, 4, 17, 12, 0, 0);
        
        // When & Then
        assertEquals("Invalid duration", DateTimeUtil.formatDuration(null, dateTime));
        assertEquals("Invalid duration", DateTimeUtil.formatDuration(dateTime, null));
    }
}