import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz
import re
from dateutil import parser as date_parser

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; MizzouCal/1.0)'}

SPORTS = {
    'football': {
        'url': 'https://mutigers.com/sports/football/schedule',
        'name': 'Football',
        'emoji': '🏈',
        'duration': 3.5,
    },
    'basketball': {
        'url': 'https://mutigers.com/sports/mens-basketball/schedule',
        'name': 'Men\'s Basketball',
        'emoji': '🏀',
        'duration': 2.5,
    },
    'volleyball': {
        'url': 'https://mutigers.com/sports/womens-volleyball/schedule',
        'name': 'Volleyball',
        'emoji': '🏐',
        'duration': 2.0,
    },
}

TZ = pytz.timezone('America/Chicago')

def fetch_page(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, 'lxml')

def parse_game_item(item, sport_key):
    sport = SPORTS[sport_key]
    
    # Accurate datetime from attribute
    time_el = item.find('time', class_='schedule-event-date__day') or item.find('time')
    dt_attr = time_el.get('datetime') if time_el else None
    if not dt_attr:
        return None
    try:
        dt = date_parser.parse(dt_attr)
        if dt.tzinfo is None:
            dt = TZ.localize(dt)
        else:
            dt = dt.astimezone(TZ)
        date = dt.date()
    except Exception:
        return None
    
    # Location type from class
    classes = item.get('class', [])
    location_type = 'Home' if any('home' in c for c in classes) else ('Away' if any('away' in c for c in classes) else 'Neutral')
    
    # Opponent
    opp_box = item.find(class_='schedule-default-event__opponent-box')
    if opp_box:
        opp_text = opp_box.get_text(separator=' | ', strip=True)
        # After sport name
        sport_name_clean = sport['name'].replace("'", "")
        parts = [p.strip() for p in opp_text.split('|') if p.strip()]
        opponent = parts[1] if len(parts) > 1 else parts[0]
        # Fallback clean
        opponent = re.sub(r'^(Football|Men\'s Basketball|Volleyball|Men’s Basketball)\s*', '', opponent, flags=re.I).strip()
    else:
        text = item.get_text(separator=' | ', strip=True)
        parts = [p.strip() for p in text.split('|') if p.strip()]
        opponent = 'TBD'
        for i, p in enumerate(parts):
            if p.lower() in ('vs.', 'at') and i+2 < len(parts):
                opponent = parts[i+2]
                break
    opponent = re.sub(r'#\d+(/#\d+)?\s*', '', opponent).strip()
    if not opponent or len(opponent) < 2 or opponent.lower() in ('football', 'basketball', 'volleyball'):
        return None
    
    # Score
    text = item.get_text(separator=' | ', strip=True)
    score = None
    score_match = re.search(r'(W|L)\s*\|\s*(Win|Loss)\s*\|\s*([\d\-]+)', text)
    if score_match:
        score = score_match.group(3)
    
    # Location
    loc_match = re.search(r'([A-Za-z0-9\s\.\-\']+(?:Stadium|Arena|Center|Coliseum|Gym)[^|]{0,60})', text)
    location = loc_match.group(1).strip() if loc_match else 'Columbia, Mo.'
    
    # TV
    tv_match = re.search(r'(ABC|ESPN(?:U|\+)?|SEC Network|SECN\+?|FOX|Peacock|SECN|ESPN2|CBS)', text)
    tv = tv_match.group(1) if tv_match else None
    
    return {
        'date': date,
        'datetime': dt,
        'opponent': opponent,
        'location_type': location_type,
        'location': location,
        'score': score,
        'tv': tv,
        'sport': sport['name'],
        'emoji': sport['emoji'],
        'duration': sport['duration'],
    }

def parse_schedule(soup, sport_key):
    items = soup.find_all(class_='schedule-event-item')
    games = []
    seen = set()
    for item in items:
        g = parse_game_item(item, sport_key)
        if g:
            key = (g['date'], g['opponent'])
            if key not in seen:
                seen.add(key)
                games.append(g)
    return games

def create_ics(all_games):
    cal = Calendar()
    cal.add('prodid', '-//Mizzou Sports Calendar//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', 'Mizzou Sports (Football, Basketball, Volleyball)')
    cal.add('x-wr-caldesc', 'Auto-updated Missouri Tigers schedules with final scores. Free alternative to Sync2Cal.')
    cal.add('x-wr-timezone', 'America/Chicago')
    
    for g in all_games:
        event = Event()
        
        # Summary styled after Sync2Cal
        if g['score']:
            if g['location_type'] == 'Home':
                summary = f"{g['emoji']} {g['opponent']} @ Missouri {g['score']} (Final)"
            else:
                summary = f"{g['emoji']} Missouri @ {g['opponent']} {g['score']} (Final)"
        else:
            if g['location_type'] == 'Home':
                summary = f"{g['emoji']} {g['opponent']} @ Missouri"
            else:
                summary = f"{g['emoji']} Missouri @ {g['opponent']}"
        
        event.add('summary', summary)
        
        # Datetime already parsed accurately
        dt = g['datetime']
        event.add('dtstart', dt)
        event.add('dtend', dt + timedelta(hours=g['duration']))
        
        # Description
        desc_parts = [g['sport']]
        if g['tv']:
            desc_parts.append(f"TV: {g['tv']}")
        if g['score']:
            desc_parts.append(f"Final: {g['score']}")
        desc_parts.append(f"Venue: {g['location']}")
        desc_parts.append("Auto-updated from mutigers.com — free Sync2Cal alternative")
        event.add('description', '\\n'.join(desc_parts))
        
        event.add('location', g['location'])
        
        # Stable UID
        uid = f"{g['date'].strftime('%Y%m%d')}-{re.sub(r'[^a-zA-Z0-9]', '', g['opponent'])[:30]}@mizzou-sports.cal"
        event.add('uid', uid)
        event.add('dtstamp', datetime.now(pytz.UTC))
        event.add('status', 'CONFIRMED')
        
        cal.add_component(event)
    
    return cal.to_ical()

def main():
    all_games = []
    for key in SPORTS:
        print(f"Fetching {key}...")
        try:
            soup = fetch_page(SPORTS[key]['url'])
            games = parse_schedule(soup, key)
            print(f"  Found {len(games)} games")
            all_games.extend(games)
        except Exception as e:
            print(f"  Error fetching {key}: {e}")
    
    all_games.sort(key=lambda g: g['date'])
    
    ics_bytes = create_ics(all_games)
    with open('mizzou-sports.ics', 'wb') as f:
        f.write(ics_bytes)
    print(f"Generated mizzou-sports.ics with {len(all_games)} events")

if __name__ == '__main__':
    main()
