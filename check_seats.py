"""SAT seat tracker.

Checks College Board's public test center search for one test date and
emails you (through your own Gmail) when a center in your city changes
from "No Seats Available" to having a seat.

Settings come from environment variables (all optional except the Gmail
ones, which are only needed to send email):

  TEST_DATE            test date, YYYY-MM-DD      (default 2027-03-06)
  COUNTRY              2-letter country code      (default MN)
  CITY                 city name to watch         (default ULAANBAATAR)
  GMAIL_ADDRESS        your Gmail address
  GMAIL_APP_PASSWORD   16-character Gmail app password
  ALERT_TO             where to send alerts       (default: GMAIL_ADDRESS)

Run `python check_seats.py --test-email` to send yourself a test email.
"""

import datetime
import json
import os
import smtplib
import sys
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

API_URL = "https://aru-test-center-search.collegeboard.org/prod/test-centers"
REGISTER_URL = "https://mysat.collegeboard.org/"
STATE_FILE = Path(__file__).with_name("state.json")

TEST_DATE = os.environ.get("TEST_DATE") or "2027-03-06"
COUNTRY = os.environ.get("COUNTRY") or "MN"
CITY = (os.environ.get("CITY") or "ULAANBAATAR").strip().upper()


def fetch_centers():
    """Return the list of test centers for TEST_DATE in COUNTRY."""
    query = urllib.parse.urlencode({"date": TEST_DATE, "country": COUNTRY})
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={
            "User-Agent": "sat-seat-tracker/1.0 (personal seat alert script)",
            "Accept": "application/json",
        },
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            if not isinstance(data, list):
                raise ValueError(f"unexpected response: {str(data)[:200]}")
            return data
        except Exception as error:  # network hiccup or changed response
            last_error = error
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Could not read test centers: {last_error}")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def send_email(subject, body):
    address = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not address or not password:
        print("GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set, so no email was sent.")
        print(f"--- would have sent ---\n{subject}\n\n{body}\n-----------------------")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = address
    message["To"] = os.environ.get("ALERT_TO") or address
    message.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(address, password.replace(" ", ""))
        server.send_message(message)
    print(f"Email sent: {subject}")
    return True


def describe(center):
    lines = [center.get("name", "").strip()]
    for key in ("address1", "address2", "address3"):
        if center.get(key, "").strip() and center[key].strip() != lines[0]:
            lines.append("  " + center[key].strip())
    lines.append(f"  Test center code: {center.get('code')}")
    return "\n".join(lines)


def main():
    if "--test-email" in sys.argv:
        sent = send_email(
            "SAT seat open: TEST",
            "This is a test from your SAT seat tracker. Email alerts work.",
        )
        sys.exit(0 if sent else 1)

    centers = [
        c for c in fetch_centers() if c.get("city", "").strip().upper() == CITY
    ]
    if not centers:
        # An empty list most likely means the date/country/city is wrong or
        # the site changed, so fail loudly instead of silently watching nothing.
        raise RuntimeError(f"No test centers found for {CITY} on {TEST_DATE}.")

    previous = load_state()
    same_search = previous.get("date") == TEST_DATE and previous.get("city") == CITY
    old_seats = previous.get("centers", {}) if same_search else {}

    new_seats = {}
    newly_open = []
    for center in sorted(centers, key=lambda c: c.get("name", "").upper()):
        code = str(center.get("code"))
        available = bool(center.get("seatAvailability"))
        new_seats[code] = {"name": center.get("name", "").strip(), "available": available}
        if available and not old_seats.get(code, {}).get("available", False):
            newly_open.append(center)

    open_now = [v["name"] for v in new_seats.values() if v["available"]]
    print(f"{TEST_DATE} {CITY}: {len(centers)} centers, {len(open_now)} with seats.")
    for name in open_now:
        print(f"  OPEN: {name}")

    if newly_open:
        names = ", ".join(c.get("name", "").strip() for c in newly_open)
        body = (
            f"A seat just opened for the SAT on {TEST_DATE} in {CITY.title()}:\n\n"
            + "\n\n".join(describe(c) for c in newly_open)
            + f"\n\nRegister now: {REGISTER_URL}\n"
            "Seats can be taken within minutes, so do not wait."
        )
        # Email first. If sending fails the script stops here, the state is
        # not saved, and the next run tries the alert again.
        send_email(f"SAT seat open: {names}", body)

    # The week number changes once a week, which gives the repository a small
    # commit and keeps GitHub from switching the schedule off for inactivity.
    week = datetime.date.today().strftime("%G-W%V")
    save_state({"date": TEST_DATE, "city": CITY, "week": week, "centers": new_seats})


if __name__ == "__main__":
    main()
