import requests
from ics import Calendar
from datetime import datetime, time, timedelta
from dateutil.rrule import rrulestr
import pytz  # For timezone management
import re

TIMEZONE_ALIASES = {
    "India Standard Time": "Asia/Kolkata",
    "Central Standard Time": "US/Central",
    "Eastern Standard Time": "US/Eastern",
    "Pacific Standard Time": "US/Pacific",
    "Mountain Standard Time": "US/Mountain",
}

RRULE_PATTERN = r"RRULE:(FREQ=\w+(?:;[^:]+)*)"

def preprocess_ics(ics_data):
    """
    Replace unknown TZIDs in the ICS data with known timezones.

    """

    # Check that we now know every timezone
    pattern = r";TZID=([^:]+):"  # Match ';TZID=<timezone>:'
    timezones = re.findall(pattern, ics_data)
    unknown_timezones = {tz for tz in timezones if tz not in TIMEZONE_ALIASES}
    if len(unknown_timezones) > 0:
        print("Warning: The following timezones are unknown to me", unknown_timezones)

    for unknown_tz, known_tz in TIMEZONE_ALIASES.items():
        # Replace TZID=unknown_tz with TZID=known_tz
        pattern = rf"(TZID={re.escape(unknown_tz)}:)"
        replacement = f"TZID={known_tz}:"
        ics_data = re.sub(pattern, replacement, ics_data)
    return ics_data

def extract_rrule(raw_event):
    """
    Extract the RRULE from a raw ICS event string using regex.

    :param raw_event: The raw string of an event.
    :return: The RRULE string, or None if not found.
    """
    match = re.search(RRULE_PATTERN, raw_event)
    return match.group(1) if match else None

def fetch_ics(url):
    """
    Fetch the ICS file from the given URL.
    """
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if the request failed
    return response.text

# def parse_ics(ics_data):
#     """
#     Parse the ICS data and return a list of busy time intervals.
#     """
#     calendar = Calendar(ics_data)
#     busy_intervals = []

#     for event in calendar.events:
#         busy_intervals.append((event.begin.datetime, event.end.datetime))

#     # Sort intervals for easier processing
#     busy_intervals.sort(key=lambda interval: interval[0])
#     return busy_intervals

def parse_ics(ics_data, start_date=None, end_date=None):
    """
    Parse ICS data and handle recurring events.

    :param ics_data: The raw ICS file data as a string.
    :param start_date: The start date to limit recurring event expansion.
    :param end_date: The end date to limit recurring event expansion.
    :return: A list of tuples (start, end) for all events, including expanded recurrences.
    """
    calendar = Calendar(ics_data)
    busy_intervals = []

    # Default date range for recurrence expansion
    if start_date is None:
        start_date = datetime.now()
    if end_date is None:
        end_date = start_date + timedelta(days=30)  # Look ahead 30 days by default

    for event in calendar.events:
        # Add single occurrences
        busy_intervals.append((event.begin.datetime, event.end.datetime))

        # Handle recurring events (RRULE)
        rrule_text = extract_rrule(str(event)) #event.extra.get("RRULE")
        print("RRULE", rrule_text)
        print("end rule")
        print(event.begin.datetime)
        if rrule_text:
            # Parse the recurrence rule
            rule = rrulestr(rrule_text, dtstart=event.begin.datetime)
            print("rule", rule)

            # Expand occurrences within the date range
            for occurrence in rule.between(start_date, end_date, inc=True):
                busy_intervals.append((occurrence, occurrence + event.duration))

    # Sort intervals for easier processing
    busy_intervals.sort(key=lambda interval: interval[0])
    return busy_intervals

def calculate_availability(busy_intervals, day, timezone="US/Central"):
    """
    Calculate availability time ranges for the day.
    """
    tz = pytz.timezone(timezone)

    # Convert day_start and day_end to offset-aware datetime objects
    day_start = tz.localize(datetime.combine(day, time.fromisoformat("09:00")))
    day_end = tz.localize(datetime.combine(day, time.fromisoformat("18:00")))

    current_time = day_start
    availability = []

    for start, end in busy_intervals:
        if day_end <= current_time:
            break
        if current_time < start:
            availability.append((current_time, start))
        current_time = max(current_time, end)

    if current_time < day_end:
        availability.append((current_time, day_end))

    return availability

def format_availability(availability):
    """
    Format availability into a human-readable string.
    """
    formatted = []
    for start, end in availability:
        formatted.append(f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}")
    return "\n".join(formatted)

def next_weekdays(start_date=None, count=5):
    """
    Find the next 'count' weekdays starting from the given date.

    :param start_date: The starting date. Defaults to today.
    :param count: The number of weekdays to find. Defaults to 5.
    :return: A list of datetime.date objects representing the next weekdays.
    """
    if start_date is None:
        start_date = datetime.now().date()

    weekdays = []
    current_date = start_date

    while len(weekdays) < count:
        if current_date.weekday() < 5:  # Monday to Friday are weekdays (0-4)
            weekdays.append(current_date)
        current_date += timedelta(days=1)

    return weekdays

def main():
    url = "https://outlook.office365.com/owa/calendar/04ba613c2d4a4157a5acdf6877d43ef5@utexas.edu/62f70625763c4c05971c6a82b715e3b315530269767823688813/calendar.ics"
    timezone = "America/Chicago" # America/New_York, America/Chicago America/Los_Angeles

    try:
        ics_data = fetch_ics(url)
        ics_data = preprocess_ics(ics_data)
        busy_intervals = parse_ics(ics_data)
        all_days = next_weekdays()
        for day in all_days:
            availability = calculate_availability(busy_intervals, day, timezone=timezone)
            print(f"Availability for {day.strftime('%A (%b %d)')}")
            formatted_availability = format_availability(availability)
            print(formatted_availability)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
