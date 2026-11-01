# Mizzou Sports Calendar

Free, auto-updating iCalendar (.ics) feed for **Missouri Tigers**:

- 🏈 Football
- 🏀 Men's Basketball  
- 🏐 Women's Volleyball

Events include accurate times (America/Chicago), venues, TV info when available, and **final scores** once games finish — similar to Sync2Cal but free and limited to the teams you care about.

## How to subscribe

Add this calendar subscription URL to Apple Calendar, Google Calendar, Outlook, etc.:

```
https://raw.githubusercontent.com/cjwhdc/mizzou-sports-calendar/main/mizzou-sports.ics
```

- **Apple Calendar**: File → New Calendar Subscription → paste the URL
- **Google Calendar**: Other calendars → + → From URL → paste the URL
- **Outlook**: Add calendar → Subscribe from web → paste the URL

The feed updates automatically every 2 hours via GitHub Actions. Calendar apps typically refresh subscribed calendars every few hours (or when you open the app).

## How it works

The `generate_mizzou_calendar.py` script scrapes the official [mutigers.com](https://mutigers.com) schedule pages for the three sports, parses games (including results), and generates a standards-compliant `.ics` file.

A GitHub Action runs the script on a schedule and commits any changes.

## Manual update

You can also trigger the workflow manually from the Actions tab, or run the script locally after `pip install -r requirements.txt`.

## Notes

- Opponent names and some details are extracted from the official site HTML (best effort).
- Times come from the site’s datetime attributes.
- Score updates appear after the site posts the final result.
- This is for personal use; please respect mutigers.com’s terms.

Enjoy the free Sync2Cal-style feed!
