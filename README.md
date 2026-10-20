# M4 Parking Check

Checks where and when an **M4 residential parking permit** (boendeparkering, zone M) is valid in Göteborg:
enter a street and number (or use your location), and the app tells you whether the permit is valid there,
whether you may park at the start time, for how long, and where nearby you can stay the longest.

Your permit is valid on signs **M4, M4n, M5 and M5n**. "n" signs only cover residents weekdays 18:00–09:00
and from 15:00 the day before a Sunday or public holiday. Same spot at most 14 days in a row.

## Use it

- **Web app:** https://marwa112.github.io/m4-parking/ — open in Chrome on Android and choose *Add to Home screen*.
- **Android app:** download `m4-parking.apk` from the latest [release](../../releases) on the phone and open it.
- **Sales deck:** https://marwa112.github.io/m4-parking/deck/ (source in `docs/deck/`). Arrow keys or swipe to move between slides.

## How it stays up to date

| What | Where | When |
|---|---|---|
| Residential parking + street cleaning | Göteborgs Stad open WFS (`open.geodata.tkgbg.se`) | Every Monday (`refresh-data.yml`) |
| House numbers + street layout | OpenStreetMap | First Monday of each month, or on demand |
| Android APK | Capacitor, built by `build-apk.yml` | When the app code changes |

The Android app downloads the latest `data.json` from the web app on start, so it gets new street data
without reinstalling.

Run the refresh by hand: *Actions → Refresh parking data → Run workflow*.

## Not included

Temporary bans (roadworks, events) aren't in the open data. Always check the signs where you park.

## Data

Parking data © Göteborgs Stad, open data. Addresses and streets © OpenStreetMap contributors (ODbL).
