import argparse
from datetime import datetime, time, timedelta
from dateutil.rrule import rrulestr
import icalendar
import recurring_ical_events
import requests
import pytz  # For timezone management
import re

def fetch_ics(url):
    """
    Fetch the ICS file from the given URL.
    """
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if the request failed
    return response.text

def parse_ics(ics_data):

    """
    Parse ICS data and handle recurring events.

    :param ics_data: The raw ICS file data as a string.
    :return: A list of tuples (start, end) for all events, including expanded recurrences.
    """

    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=30)

    calendar = icalendar.Calendar.from_ical(ics_data)
    events = recurring_ical_events.of(calendar).between(start_date, end_date)

    busy_intervals = []
    for event in events:
        start = event["DTSTART"].dt
        end = event["DTEND"].dt

        busy_intervals.append((start, end))

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
        if day_end <= current_time or day_end <= start:
            break
        if current_time < start:
            availability.append((current_time, start))
        current_time = max(current_time, end)

    if current_time < day_end:
        availability.append((current_time, day_end))

    return availability

def format_availability(availability, output_timezone=None):
    """
    Format availability into a human-readable string.
    """
    formatted = []
    timefmt = '%H:%M'
    output_timezone_pretty = {
        "Asia/Kolkata": "IST",
        "US/Central": "CT",
        "US/Eastern": "ET",
        "US/Pacific": "PT",
        "US/Mountain": "MT",
    }
    tz = pytz.timezone(output_timezone)
    for start, end in availability:
        if output_timezone is not None:
            formatted.append(f"{output_timezone_pretty[output_timezone]} {start.astimezone(tz).strftime(timefmt)} - {end.astimezone(tz).strftime(timefmt)}, CT: {start.strftime(timefmt)} - {end.strftime(timefmt)}")
        else:
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
    with open("ical_url", "r") as f:
        url = f.read()
    timezone = "America/Chicago"

    parser = argparse.ArgumentParser(description="Process a timezone input.")
    parser.add_argument(
        "timezone",
        type=str,
        default="US/Central",
        nargs="?",
        help="The timezone to process (e.g., America/Chicago)."
    )

    args = parser.parse_args()
    output_timezone = args.timezone

    # Validate the timezone
    if output_timezone not in pytz.all_timezones:
        print(f"Invalid timezone: {timezone_input}")
        print("Here are some valid timezones:")
        print(", ".join(pytz.common_timezones[:10]) + ", ...")

    try:
        ics_data = fetch_ics(url)
        busy_intervals = parse_ics(ics_data)
        all_days = next_weekdays()
        for day in all_days:
            availability = calculate_availability(busy_intervals, day, timezone=timezone)
            print(f"Availability for {day.strftime('%A (%b %d)')}")
            formatted_availability = format_availability(availability, output_timezone)
            print(formatted_availability)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
