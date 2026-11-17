This chapter defines how the app organises its content. New features must follow these rules, so that the app stays one consistent tool. Each rule has an ID (IA-nn). A change to a rule needs a new version of this document.

## IA-01 One screen, fixed regions {#IA-01}

The app is one scrolling screen. It has no pages, tabs or menus. The screen has eight regions in a fixed order. The order follows the questions of the user, from "where am I?" to "what is around me?".

[[figure IA-01-screen-order "IA-01 The eight regions of the screen, top to bottom."]]

| Region | Content | Shown |
|---|---|---|
| R1 Header | App name, permit (M4) | Always |
| R2 Week banner | Week number, odd or even, next week, date | Always |
| R3 My car | Saved car, free time, pay or move | Only when a car is saved |
| R4 Question | Street, number, location, start time, until time | Always |
| R5 Answer | Result cards for one address | After a check |
| R6 Alternatives | Longest stays nearby | After a check |
| R7 Context | Map and legend | After a check |
| R8 Footer | Rules summary, data date, disclaimer | Always |

**Rule for new features.** Put new content into the region that answers the same question. Do not add a region between R4 and R5. Do not add a new navigation layer. If a feature does not fit a region, update IA-01 first.

## IA-02 Answer first, details after {#IA-02}

Each result gives the answer before the explanation. The order in R5 is fixed:

1. Is the permit valid here? (Permit valid here / Not valid on your side / Permit not valid here)
2. Can I park at the start time? (You may park now / Not allowed now)
3. Until when, or from when? (a time, and the time left)
4. Why? (the reason: street cleaning, night sign, 14-day limit)
5. Details (sign, street cleaning rule, spaces, other sections)
6. Action (I parked here)

**Rule for new features.** A new card in R5 or R3 has a one-line answer as its title. The details follow below the title. An action button comes last.

## IA-03 Content objects {#IA-03}

The app works with a small set of content objects. Each object has one name in the interface, and the glossary defines it.

[[figure IA-02-objects "IA-03 Content objects and how they relate."]]

| Object | Name on screen | Key properties |
|---|---|---|
| Permit | Permit M4 | Zone letter, taxa |
| Address | Street + number, for example Sveagatan 12 | Position, side of street |
| M section | Sign text, for example Boende M4n | Sign, spaces, position |
| Street cleaning rule | No parking Wed 09–12 · odd wks | Weekday, hours, week type, season |
| Paid parking | Taxa 1 | Price, maximum time, platskod |
| Moment | Start time, Until | Live (now) or selected |
| Verdict | You may park now / Not allowed now | End or start time, reason |
| Suggestion | Street + numbers | Stay, end, distance |
| Parked car | My car | Address, M section, parked at |
| Week | Week 47 · Odd week | ISO number, odd or even |

**Rule for new features.** Use an existing object if possible. A new object needs a glossary entry, a name on screen and a place in IA-03.

## IA-04 States and their signs {#IA-04}

The app uses a fixed set of states. Each state has the same colour, shape and words everywhere: in result cards, on the map, in labels and in reminders.

| State | Words | Card | Map | Label |
|---|---|---|---|---|
| Allowed | You may park | Blue card, mark P | Solid blue line | – |
| Not allowed | Not allowed | Orange striped card, mark ✕ | Solid red line | – |
| Across the street | Across the street | Dashed card, mark ↔ | – | – |
| Street cleaning soon | No parking … | – | – | Red, yellow text, ⚠ |
| Street cleaning later | Cleaning … | – | – | White, dashed, outline ⚠ |
| Other parking | … not valid | – | Grey dotted line | Dotted white |
| Pay | Pay now or move | Orange striped card, mark kr | – | – |

**Rule for new features.** Map a new state to an existing row if possible. A new state needs a word, a shape or pattern and a colour that is not a red/green pair (NFR-ACC-001, NFR-ACC-002).

## IA-05 Time model {#IA-05}

All results refer to one moment or one period.

- The **start time** is the current time by default. Then the time is live, and the app uses the word "now".
- When the user selects a start time, the app uses "at the start time" and shows that time.
- "Today" and "tomorrow" always mean the current date.
- A date that is not today or tomorrow shows the weekday, the date, the week number and odd or even.
- Times use the 24-hour clock. Durations use d, h and min.

**Rule for new features.** Every new time-based answer uses this model and these words.

## IA-06 Controlled words {#IA-06}

The interface uses one word for one thing. Do not use the words in the last column.

| Use | Meaning | Do not use |
|---|---|---|
| permit | the M4 residential permit | licence, pass |
| M section | a part of a street with an M sign | spot, bay, zone |
| street cleaning | the hours with a parking ban for cleaning | sweeping, service day |
| start time | the moment that the app checks | selected time, check time |
| until time | the end of a planned stay | end time (as a field name) |
| parking place | the address dot on the map | pin, marker |
| move the car | the user must leave the place | relocate |
| pay | start a payment in another app | buy, purchase |

## IA-07 Navigation and links {#IA-07}

- The user moves through the screen by scrolling.
- A tap on a suggestion scrolls to the map (R7).
- A tap on a reminder opens the app at the My car card (R3).
- Buttons that leave the app say where they go, for example "Open Parkering Göteborg".

## IA-08 What the app stores {#IA-08}

| Item | Where | When it is deleted |
|---|---|---|
| Last checked address | localStorage | At the next check |
| Parked car | localStorage | "I moved the car" |
| Newer street data | localStorage (Android app) | At the next newer download |
| App files and data | Service worker cache (web app) | When the app version changes |

The app stores nothing on a server (NFR-PRIV-001).

## IA-09 Show more only when needed {#IA-09}

- The map labels only the searched street at the first zoom level, and every section when the user zooms in.
- The My car card appears only when a car is saved.
- Alternatives and the map appear only after a check.
- The details of a result (sign, rule, spaces) come after the answer.

## IA-10 Checklist for a new feature {#IA-10}

1. Name the user question that the feature answers.
2. Select the region (IA-01) that answers that question.
3. Write the answer line first, then the details (IA-02).
4. Use existing content objects (IA-03) and states (IA-04).
5. Use the time model (IA-05) and the controlled words (IA-06).
6. Use design system components (chapter Design system).
7. Add the requirements, screens and tests to this document.
