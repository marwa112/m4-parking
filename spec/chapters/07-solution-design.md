This chapter records the main design decisions (ADR-nnn) and the logic of the rules engine. Each decision gives the situation, the decision and the result.

## AR-07 Rules engine {#AR-07}

The rules engine answers one question: is parking allowed in M section s at time t? `nextChange()` asks this question every 15 minutes ahead, until the answer changes.

[[figure AR-07-rules "AR-07 Decision flow of status(t, s)."]]

## ADR-001 A static app with the data inside {#ADR-001}

- **Situation.** The app must work in the street, often with a weak network. The project has no budget for a server.
- **Decision.** The app is one static web page with one data file. GitHub Pages hosts it. There is no server.
- **Result.** The app works offline and costs nothing to run. The data is as new as the last weekly refresh.

## ADR-002 City data for the rules, OpenStreetMap for addresses {#ADR-002}

- **Situation.** The city data has the signs and the street cleaning, but no house numbers.
- **Decision.** The app takes all rules from the city, and the house numbers and streets from OpenStreetMap.
- **Result.** The user can search by address. The position of a house number has an accuracy of some metres. The app says when it estimates a position.

## ADR-003 No API keys and no payment in the app {#ADR-003}

- **Situation.** The repository is public. Keys in a public repository are not secret.
- **Decision.** The app uses only open data without keys. Payment happens in the Parkering Göteborg app or by SMS, and the user approves it there.
- **Result.** No secret exists to leak. The app never holds card data.

## ADR-004 Capacitor for the Android app {#ADR-004}

- **Situation.** The user wants an Android app with reminders, without a store account.
- **Decision.** Capacitor wraps the web app in an Android shell and adds notifications and an app launcher.
- **Result.** One code base for the web app and the Android app. The APK installs directly from GitHub Releases.

## ADR-005 A map drawn by the app {#ADR-005}

- **Situation.** Map tiles from Google need a key and an account. The colours of a tile map cannot be controlled.
- **Decision.** The app draws streets, sections and labels as SVG from the data file.
- **Result.** The map works offline, needs no key and uses only colours without red/green pairs.

## ADR-006 Time in steps of 15 minutes {#ADR-006}

- **Situation.** The rules change at full and half hours. The app must find the next change quickly.
- **Decision.** The engine checks the status every 15 minutes, for up to 15 days.
- **Result.** Simple code that is easy to test. A rule at another minute would show up to 14 minutes late.

## ADR-007 Side of the street from the street centre line {#ADR-007}

- **Situation.** The two sides of a street can have different signs.
- **Decision.** The app uses the OpenStreetMap centre line to find which side the house number and each section are on.
- **Result.** The app checks the side of the house number first, and shows the other side as an option.

## ADR-008 Colours with a second sign {#ADR-008}

- **Situation.** The main user is colour blind.
- **Decision.** No red/green pairs. Each colour that has a meaning also has a word, an icon, a stripe, a dash or a dot.
- **Result.** The design system (DS-COL, DS-CMP) applies this rule to every element.

## ADR-009 Weekly city data, monthly addresses {#ADR-009}

- **Situation.** Signs and street cleaning rules change often. Addresses change rarely. OpenStreetMap asks users to keep the load low.
- **Decision.** City data every Monday. OpenStreetMap data on the first Monday of each month.
- **Result.** Current rules, and a low load on OpenStreetMap.

## ADR-010 Never overwrite a version {#ADR-010}

- **Situation.** The user wants every change to be a new version.
- **Decision.** Every change is a new commit. The build scripts refuse to overwrite a version file. Before a large change, the earlier state goes to a named branch.
- **Result.** Each earlier version stays available.

## ADR-011 A new test key for each APK {#ADR-011}

- **Situation.** A permanent signing key needs a safe place outside the public repository.
- **Decision.** Each build signs the APK with a new test key.
- **Result.** The user must uninstall the old version before an update. A permanent key in GitHub Secrets removes this step later (NFR-SEC-004).
