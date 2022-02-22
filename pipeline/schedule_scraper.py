#!/usr/bin/env python

from datetime import datetime, timezone
import math
import re
import requests

from bs4 import BeautifulSoup

import machines

URL = "https://dss.gb.nrao.edu/schedule/public?tz=UTC"

class Scraper(object):
    def __init__(self, backend="BTL"):
        response = requests.get(URL)
        self.backend = backend
        self.html = response.text
        self.soup = BeautifulSoup(self.html, features="html5lib")

        # A list of (start, end) pairs for when we are recording
        self.schedule = []
        
        rows = self.soup.find_all("tr")
        year = None
        month = None
        day = None
        for row in rows:
            # Check if a header shows the date
            for th in row.find_all("th"):
                text = th.get_text().strip()
                m = re.match(r"^([0-9]{4})-([0-9]{2})-([0-9]{2}) \([A-Z]*\)$", text)
                if m:
                    year = int(m.group(1))
                    month = int(m.group(2))
                    day = int(m.group(3))

            # Check for rows that are first-element times, last-element "BTL"
            tds = row.find_all("td")
            if tds and year is not None and self.backend in tds[-1].get_text():
                text = tds[0].get_text().strip()
                m = re.match(r"^.?([0-9]{2}):([0-9]{2}) - ([0-9]{2}):([0-9]{2}).?$", text)
                if m:
                    start_hour = int(m.group(1))
                    start_minute = int(m.group(2))
                    end_hour = int(m.group(3))
                    end_minute = int(m.group(4))
                    start_time = datetime(year, month, day, start_hour, start_minute, tzinfo=timezone.utc)
                    end_time = datetime(year, month, day, end_hour, end_minute, tzinfo=timezone.utc)
                    self.schedule.append((start_time, end_time))

                    
    def __str__(self):
        header = f"{len(self.schedule)} {self.backend} observations on the schedule."
        free = self.free_hours()
        if math.isinf(free):
            footer = "No upcoming observations scheduled."
        else:
            footer = f"We have an observation scheduled in {free:.1f} hours."
        return "\n".join([header] + [f"{a} - {b}" for (a, b) in self.schedule] + [footer])

    def is_observing(self):
        now = datetime.now(timezone.utc)
        for start, end in self.schedule:
            if start <= now <= end:
                return True
        return False

    def free_hours(self):
        """
        Estimates how many hours until we start observing.
        If we don't know, guess infinity.
        """
        if self.is_observing():
            return 0
        now = datetime.now(timezone.utc)

        estimate = float("inf")
        for start, _ in self.schedule:
            if start < now:
                continue
            seconds = (start - now).total_seconds()
            hours = seconds / 3600
            estimate = min(hours, estimate)

        return estimate
        
        

if __name__ == "__main__":
    s = Scraper()
    print(s)
    
