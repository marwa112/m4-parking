This chapter shows how the parts of M4 Parking Check fit together. Each diagram has an ID (AR-nn). The diagram sources are text files in `spec/diagrams/`, so a change to the architecture is a change to a file in the repository.

## AR-01 System context {#AR-01}

M4 Parking Check runs on the phone of the user. It has no server of its own. GitHub builds and hosts everything. The app opens other apps for payment. It does not handle money.

[[figure AR-01-context "AR-01 System context: the user, the app, the data sources and the payment apps."]]

| External system | What the app gets or gives | How often |
|---|---|---|
| Göteborgs Stad open WFS | Residential parking, street cleaning, paid parking | Every Monday |
| OpenStreetMap | House numbers, street lines | First Monday of the month |
| GitHub | Hosting of the web app, the APK and this document | On each change |
| Parkering Göteborg app | Payment, started and approved by the user | When the user taps a button |
| SMS 72 430 | Payment by SMS, sent by the user | When the user taps Send |

## AR-02 Components {#AR-02}

The app has four layers. The user interface and the app logic are one HTML file with JavaScript. The data is one JSON file. The Android shell exists only in the APK.

[[figure AR-02-components "AR-02 Components in four layers. AR-05 and AR-06 show the flows between them."]]

| Component | Code | Job |
|---|---|---|
| Street search | `resolveStreet()` | Finds the M-zone street from what the user typed |
| Address location | `locate()`, `makeSide()` | Finds the house number position and its side of the street |
| Rules engine | `status()`, `nextChange()` | Says if parking is allowed at a time, and when that changes |
| Calendar | `isoWeek()`, `holidays()` | ISO week numbers and Swedish public holidays |
| Pay-or-move plan | `plan()`, `estCost()` | Free time, then pay or move, for the saved car |
| Map | `drawMap()`, `zoomAt()` | Draws streets, sections and labels as SVG |
| Label placer | `tryLabel()`, `fits()` | Places labels without overlap |
| Reminders | `scheduleCar()` | Schedules Android notifications |

## AR-03 Data pipeline {#AR-03}

The pipeline turns three sources into one compact file, `docs/data.json`. It stops if the result looks incomplete.

[[figure AR-03-pipeline "AR-03 Data pipeline, from the open data to data.json."]]

## AR-04 Deployment {#AR-04}

GitHub Actions does all builds. GitHub Pages serves the web app, the sales deck and this document. GitHub Releases holds each APK.

[[figure AR-04-deployment "AR-04 Deployment: workflows, hosting and the phone."]]

| Workflow | Starts | Result |
|---|---|---|
| Refresh parking data | Every Monday 02:17 UTC, or by hand | New `docs/data.json` if the data changed |
| Build Android app | A change to the app, the icons or `app/` | APK as release v1.n |
| pages-build-deployment | Each change on `main` | New version of the website |

## AR-05 Check an address {#AR-05}

[[figure AR-05-seq-check "AR-05 Sequence: the user checks an address."]]

## AR-06 Park, then pay or move {#AR-06}

[[figure AR-06-seq-pay "AR-06 Sequence: the user parks, then pays or moves the car."]]

## AR-08 Technology {#AR-08}

| Part | Technology | Version |
|---|---|---|
| App | HTML, CSS, JavaScript, no framework | – |
| Fonts | Overpass, Overpass Mono (Google Fonts) | – |
| Android shell | Capacitor | 6.2.0 |
| Android plugins | Local notifications, App launcher, App | 6.1.3, 6.0.4, 6.0.3 |
| Pipeline | Python, pyproj | 3.12, 3.6.1 |
| Coordinates | SWEREF 99 12 00 (EPSG:3007) to WGS 84 | – |
| Hosting | GitHub Pages, GitHub Releases | – |
| Build | GitHub Actions | – |

## AR-09 Data file {#AR-09}

`docs/data.json` uses arrays, not named fields, to keep the file small (about 500 kB).

| Key | Content |
|---|---|
| `v` | Download date |
| `streets` | Names of the M-zone streets |
| `seg` | M sections: street, taxa, night sign, spaces, coordinates, street cleaning rules, paid parking |
| `paid` | Paid parking: taxa, platskod, price text, maximum time, time limit |
| `addr` | Addresses: street, number, letter, latitude, longitude |
| `rnames`, `roads` | Street names and street lines for the map |
| `olabels`, `other` | Other parking for the map |
