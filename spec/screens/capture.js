// Captures the screen sequences for the specification.
//
// Usage (from the repository root, with the web app served on http://localhost:8765/):
//   cd docs && python3 -m http.server 8765 &
//   SCREENS_VERSION=0.3 FONT_DIR=/path/to/node_modules/@fontsource node spec/screens/capture.js
//
// Writes docs/spec/screens/v<version>/SC-*.webp|png and manifest.json.
// It never overwrites: an existing version folder stops the script.
// The clock is fixed, so every capture of a version shows the same times.
// Mock-ups (phone-only screens) carry a MOCK-UP band and "mock": true in the manifest.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const VERSION = process.env.SCREENS_VERSION || '0.3';
const OUT = path.join(ROOT, 'docs', 'spec', 'screens', 'v' + VERSION);
const URL = process.env.APP_URL || 'http://localhost:8765/';
const BASE = '2026-11-17T08:45:00';          // Tuesday, ISO week 47 (odd week)
const W = 412, H = 892;

if (fs.existsSync(OUT)) { console.error(`${OUT} exists. A version is never overwritten.`); process.exit(1); }
fs.mkdirSync(OUT, { recursive: true });

// Fonts: the app uses Overpass from Google Fonts. Serve local copies when FONT_DIR is set.
let fontCss = '';
if (process.env.FONT_DIR) {
  const ff = (fam, file, w) => `@font-face{font-family:'${fam}';font-weight:${w};src:url(data:font/woff2;base64,${fs.readFileSync(path.join(process.env.FONT_DIR, file)).toString('base64')}) format('woff2')}`;
  fontCss = [400, 600, 800, 900].map(w => ff('Overpass', `overpass/files/overpass-latin-${w}-normal.woff2`, w)).join('') +
    [500, 700].map(w => ff('Overpass Mono', `overpass-mono/files/overpass-mono-latin-${w}-normal.woff2`, w)).join('');
}

const manifest = { version: VERSION, clock: BASE, size: [W, H], screens: [] };

// ---------- helpers ----------
async function newPage(browser, { time = BASE, geo = null } = {}) {
  const ctx = await browser.newContext({
    viewport: { width: W, height: H }, deviceScaleFactor: 2, isMobile: true, hasTouch: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36',
    geolocation: geo || undefined, permissions: geo ? ['geolocation'] : [],
  });
  if (fontCss) await ctx.route('**/fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: fontCss }));
  await ctx.route('**/marwa112.github.io/**', r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date(time));
  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.waitForFunction(() => document.querySelectorAll('#sug .sg').length > 0 || document.querySelector('#steps .step'));
  return p;
}
async function check(p, street, num, { when = null, until = '' } = {}) {
  await p.evaluate(([s, n, w, u]) => {
    const $ = id => document.getElementById(id);
    $('street').value = s; $('num').value = n;
    if (w) { $('when').value = w; $('when').dispatchEvent(new Event('input')); } else $('nowBtn').click();
    $('until').value = u; $('f').requestSubmit();
  }, [street, num, when, until]);
  await p.waitForTimeout(350);
}
async function scrollTo(p, sel, offset = 8) {
  await p.evaluate(([s, o]) => { const e = document.querySelector(s); window.scrollTo(0, e.getBoundingClientRect().top + scrollY - o); }, [sel, offset]);
  await p.waitForTimeout(150);
}
// marks: [{sel, n, text}] -> positions in % of the image, from the element boxes
async function shot(p, def, marks = [], clipSel = null) {
  const file = `${def.id}.webp`;
  let clip = null;
  if (clipSel) { const b = await (await p.$(clipSel)).boundingBox(); clip = { x: b.x, y: b.y, width: b.width, height: b.height }; }
  const boxW = clip ? clip.width : W, boxH = clip ? clip.height : H;
  const pos = [];
  for (const m of marks) {
    const el = await p.$(m.sel);
    if (!el) { console.warn('mark not found', def.id, m.sel); continue; }
    const b = await el.boundingBox();
    if (!b) continue;
    const x = (b.x - (clip ? clip.x : 0)) + (m.dx ?? Math.min(b.width - 6, 14));
    const y = (b.y - (clip ? clip.y : 0)) + (m.dy ?? 6);
    pos.push({ n: m.n, x: +(x / boxW * 100).toFixed(2), y: +(y / boxH * 100).toFixed(2), text: m.text });
  }
  const buf = await p.screenshot(clip ? { clip, type: 'png' } : { type: 'png' });
  fs.writeFileSync(path.join(OUT, file.replace('.webp', '.png')), buf);
  manifest.screens.push({ ...def, file: file.replace('.webp', '.png'), w: Math.round(boxW), h: Math.round(boxH), marks: pos, mock: !!def.mock });
  console.log(def.id, pos.length, 'marks');
}
async function mockOverlay(p, htmlBody, css = '') {
  await p.evaluate(([b, c]) => {
    const st = document.createElement('style'); st.textContent = `
      .mk-dim{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9998}
      .mk-band{position:fixed;left:-40px;right:-40px;top:58%;transform:rotate(-12deg);background:#ef7e0d;color:#272728;font:900 22px/1 system-ui,sans-serif;letter-spacing:.2em;text-align:center;padding:10px 0;z-index:10001;opacity:.92}
      .mk-tag{position:fixed;left:8px;top:8px;background:#272728;color:#fff;font:700 12px/1 system-ui,sans-serif;padding:6px 8px;border-radius:4px;z-index:10002;letter-spacing:.06em}
      ${c}`;
    document.head.appendChild(st);
    const w = document.createElement('div'); w.innerHTML = b; document.body.appendChild(w);
    const band = document.createElement('div'); band.className = 'mk-band'; band.textContent = 'MOCK-UP · NOT A REAL CAPTURE'; document.body.appendChild(band);
    const tag = document.createElement('div'); tag.className = 'mk-tag'; tag.textContent = 'MOCK-UP'; document.body.appendChild(tag);
  }, [htmlBody, css]);
  await p.waitForTimeout(100);
}
async function mockPage(browser, html) {   // a stand-alone mock-up screen (another app)
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  await p.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
    body{margin:0;font:16px/1.4 system-ui,Roboto,sans-serif;background:#f3f4f6;color:#111;height:${H}px;overflow:hidden}
    .sb{height:28px;display:flex;justify-content:space-between;align-items:center;padding:0 16px;font-size:13px;font-weight:600}
    </style></head><body><div class="sb"><span>08:45</span><span>▲ ◆ ▮</span></div>${html}</body></html>`);
  return p;
}
const DLG_CSS = `.mk-dlg{position:fixed;left:24px;right:24px;top:32%;background:#fff;color:#111;border-radius:22px;padding:22px 22px 12px;z-index:9999;font:15px/1.45 system-ui,Roboto,sans-serif;box-shadow:0 20px 60px rgba(0,0,0,.4)}
  .mk-dlg h3{margin:6px 0 10px;font-size:18px;font-weight:600} .mk-dlg .opt{display:block;width:100%;text-align:center;padding:12px;margin:6px 0;border-radius:20px;background:#e8eefc;font-weight:600;color:#0b3d91}`;

// ---------- the sequences ----------
(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  let p;

  // FE-01.01 Street search
  p = await newPage(b);
  await p.evaluate(() => { const $ = id => document.getElementById(id); $('street').value = ''; $('num').value = '';
    $('resTitle').textContent = 'Result'; $('steps').innerHTML = '<p class="hint">Enter a street and a number, or use your location.</p>'; $('sugSec').hidden = true; $('mapSec').hidden = true; });
  await shot(p, { id: 'SC-01.01-1', fe: 'FE-01.01', title: 'Empty search form', caption: 'The user opens the app. The user types the street name in Street and the house number in Number.', frs: ['FR-01.01.001'] },
    [{ sel: '#street', n: 1, text: 'Street name' }, { sel: '#num', n: 2, text: 'House number' }, { sel: '.go', n: 3, text: 'Check' }]);
  await p.evaluate(() => { const $ = id => document.getElementById(id); $('street').value = 'linne gatan'; $('num').value = '40'; });
  await shot(p, { id: 'SC-01.01-2', fe: 'FE-01.01', title: 'Street name without accent', caption: 'The user types "linne gatan" without the accent and with a space. The user taps Check.', frs: ['FR-01.01.002', 'FR-01.01.003'] },
    [{ sel: '#street', n: 1, text: 'Name as typed' }, { sel: '.go', n: 2, text: 'Check' }]);
  await check(p, 'linne gatan', '40');
  await p.evaluate(() => scrollTo(0, 0));
  await shot(p, { id: 'SC-01.01-3', fe: 'FE-01.01', title: 'Corrected street name', caption: 'The app finds Linnégatan. The app shows the name that it uses above the result.', frs: ['FR-01.01.006'] },
    [{ sel: '#fuzzy', n: 1, text: 'Name that the app uses' }, { sel: '#resTitle', n: 2, text: 'Result title' }]);
  await p.context().close();

  // FE-01.02 House number location
  p = await newPage(b);
  await check(p, 'Sveagatan', '14A'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-01.02-1', fe: 'FE-01.02', title: 'House number with a letter', caption: 'The user enters 14A. The app finds the position of Sveagatan 14A and checks the signs there.', frs: ['FR-01.02.001', 'FR-01.02.002'] },
    [{ sel: '#resTitle', n: 1, text: 'Address with letter' }, { sel: '#steps .step', n: 2, text: 'Result for that position' }]);
  await check(p, 'Sveagatan', '26'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-01.02-2', fe: 'FE-01.02', title: 'Estimated position', caption: 'The address data has no Sveagatan 26. The app estimates the position from the nearest even numbers and says so.', frs: ['FR-01.02.004', 'FR-01.02.005'] },
    [{ sel: '#steps .step .s-sub', n: 1, text: 'Estimate note' }]);
  await p.context().close();

  // FE-01.03 Permit validity
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-01.03-1', fe: 'FE-01.03', title: 'Permit valid', caption: 'Sveagatan 12 has the sign Boende M4. The app shows "Permit valid here" and the sign text.', frs: ['FR-01.03.001', 'FR-01.03.002', 'FR-01.03.004'] },
    [{ sel: '#steps .step', n: 1, text: 'Permit valid' }, { sel: '#steps .kv', n: 2, text: 'Sign and cleaning' }]);
  await check(p, 'Kungsgatan', '5'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-01.03-2', fe: 'FE-01.03', title: 'No M signs on the street', caption: 'Kungsgatan has no M section. The app shows "Permit not valid here".', frs: ['FR-01.03.003'] },
    [{ sel: '#steps .step', n: 1, text: 'Permit not valid' }]);
  await check(p, 'Tredje Långgatan', '39'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-01.03-3', fe: 'FE-01.03', title: 'M section too far away', caption: 'Tredje Långgatan has M sections, but not near number 39. The app gives the distance to the nearest M section.', frs: ['FR-01.03.005', 'FR-01.03.006'] },
    [{ sel: '#steps .step', n: 1, text: 'Distance to nearest M section' }]);
  await p.context().close();

  // FE-01.04 Side of the street
  p = await newPage(b);
  await check(p, 'Linnégatan', '8'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-01.04-1', fe: 'FE-01.04', title: 'Not valid on this side', caption: 'Linnégatan 8 has paid parking on its side. The app names it and shows the M section across the street.', frs: ['FR-01.04.001', 'FR-01.04.002', 'FR-01.04.003', 'FR-01.04.004'] },
    [{ sel: '#steps .step:nth-child(1)', n: 1, text: 'Not valid on your side' }, { sel: '#steps .step:nth-child(2)', n: 2, text: 'Section across the street' }, { sel: '#steps .step:nth-child(3)', n: 3, text: 'Result for that section' }]);
  await p.context().close();

  // FE-02.01 Night signs
  p = await newPage(b, { time: '2026-11-17T10:00:00' });
  await check(p, 'Linnégatan', '40'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-02.01-1', fe: 'FE-02.01', title: 'Night sign in the daytime', caption: 'At 10:00 on a Tuesday, the night sign M4n does not allow parking. Parking is allowed again from 18:00.', frs: ['FR-02.01.001'] },
    [{ sel: '#steps .step:nth-child(2)', n: 1, text: 'Not allowed now' }, { sel: '#steps .step:nth-child(2) strong', n: 2, text: 'Allowed from 18:00' }]);
  await p.context().close();
  p = await newPage(b, { time: '2026-11-21T15:30:00' });
  await check(p, 'Linnégatan', '40'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-02.01-2', fe: 'FE-02.01', title: 'Night sign before a Sunday', caption: 'At 15:30 on a Saturday, the night sign allows parking. The day before a Sunday, the night period starts at 15:00.', frs: ['FR-02.01.002', 'FR-02.01.003'] },
    [{ sel: '#steps .step:nth-child(2)', n: 1, text: 'Allowed from 15:00' }]);
  await p.context().close();

  // FE-02.02 Street cleaning
  p = await newPage(b, { time: '2026-11-17T10:30:00' });
  await check(p, 'Seminariegatan', '10'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-02.02-1', fe: 'FE-02.02', title: 'Street cleaning now', caption: 'Seminariegatan 10 has street cleaning on Tuesdays 09:00–12:00 in odd weeks. Week 47 is odd, so parking is not allowed.', frs: ['FR-02.02.001', 'FR-02.02.002', 'FR-02.02.003', 'FR-02.02.004'] },
    [{ sel: '#steps .step:nth-child(2)', n: 1, text: 'Not allowed now' }, { sel: '#steps .kv .ban', n: 2, text: 'Cleaning rule' }]);
  await p.context().close();

  // FE-02.03 14-day limit (via until time)
  p = await newPage(b);
  await check(p, 'Vegagatan', '11', { until: '2026-12-04T08:45' }); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-02.03-1', fe: 'FE-02.03', title: '14-day limit', caption: 'The user asks for a stay of 17 days. The app stops the stay after 14 days and tells the user to move the car.', frs: ['FR-02.03.001'] },
    [{ sel: '#steps .step:nth-child(2)', n: 1, text: '14-day limit reached' }]);
  await p.context().close();

  // FE-03.01 Result for one moment
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-03.01-1', fe: 'FE-03.01', title: 'Allowed now, until when', caption: 'The app answers yes first. Then it gives the end time, the time left and the reason: street cleaning on Wednesday.', frs: ['FR-03.01.001', 'FR-03.01.002', 'FR-03.01.004'] },
    [{ sel: '#steps .step:nth-child(2) .s-big', n: 1, text: 'Yes or no' }, { sel: '#steps .step:nth-child(2) strong', n: 2, text: 'End time' }, { sel: '#steps .step:nth-child(2) .s-sub:last-child', n: 3, text: 'Reason' }]);
  await p.context().close();

  // FE-03.02 Start time
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await p.evaluate(() => scrollTo(0, 0)); await scrollTo(p, '#when', 120);
  await shot(p, { id: 'SC-03.02-1', fe: 'FE-03.02', title: 'Start time field', caption: 'The start time shows the current time. The user can select another date and time, or tap Now.', frs: ['FR-03.02.001', 'FR-03.02.002', 'FR-03.02.003'] },
    [{ sel: '#when', n: 1, text: 'Start time' }, { sel: '#nowBtn', n: 2, text: 'Now' }]);
  await check(p, 'Sveagatan', '12', { when: '2026-11-18T10:00' }); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-03.02-2', fe: 'FE-03.02', title: 'Result for a start time', caption: 'For Wednesday 10:00, the result says "at the start time", not "now". It shows the start time.', frs: ['FR-03.02.004', 'FR-03.02.005', 'FR-03.02.006'] },
    [{ sel: '#steps .step:nth-child(2) .s-big', n: 1, text: 'At the start time' }, { sel: '#steps .step:nth-child(2) .s-sub', n: 2, text: 'Start time shown' }]);
  await p.context().close();

  // FE-03.03 Until time
  p = await newPage(b);
  await check(p, 'Sveagatan', '12', { until: '2026-11-18T08:00' }); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-03.03-1', fe: 'FE-03.03', title: 'Whole stay allowed', caption: 'The user enters Until Wednesday 08:00. The whole stay is allowed. The app also shows the latest possible end.', frs: ['FR-03.03.001', 'FR-03.03.004'] },
    [{ sel: '#steps .step:nth-child(2) .s-big', n: 1, text: 'Whole stay allowed' }, { sel: '#steps .step:nth-child(2) .s-sub:last-child', n: 2, text: 'Latest end' }]);
  await check(p, 'Sveagatan', '12', { until: '2026-11-18T18:00' }); await scrollTo(p, '#result');
  await shot(p, { id: 'SC-03.03-2', fe: 'FE-03.03', title: 'Stay not allowed in full', caption: 'With Until Wednesday 18:00, street cleaning interrupts the stay. The app says when to move the car and when parking is allowed again.', frs: ['FR-03.03.005', 'FR-03.03.006'] },
    [{ sel: '#steps .step:nth-child(2) .s-big', n: 1, text: 'Not for your whole stay' }, { sel: '#steps .step:nth-child(2) .s-sub:last-child', n: 2, text: 'Move by, allowed again' }]);
  await p.context().close();

  // FE-04.01 Week banner
  p = await newPage(b);
  await shot(p, { id: 'SC-04.01-1', fe: 'FE-04.01', title: 'Week banner', caption: 'The top of the app shows week 47 and the words "Odd week". It also shows the next week and the date.', frs: ['FR-04.01.001', 'FR-04.01.002', 'FR-04.01.003', 'FR-04.01.004'] },
    [{ sel: '#wkNum', n: 1, text: 'Week number' }, { sel: '#wkPill', n: 2, text: 'Week type' }, { sel: '#wkNext', n: 3, text: 'Next week and date' }], 'section[aria-label="Week number"]');
  await p.context().close();

  // FE-04.02 Cleaning labels
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await scrollTo(p, '#steps .kv');
  await shot(p, { id: 'SC-04.02-1', fe: 'FE-04.02', title: 'Red cleaning warning', caption: 'Street cleaning on Wednesday is less than 7 days away. The result shows a red label with yellow text, the rule and the next date.', frs: ['FR-04.02.001', 'FR-04.02.002', 'FR-04.02.006', 'FR-04.02.008'] },
    [{ sel: '#steps .kv .ban', n: 1, text: 'Red warning label' }]);
  await scrollTo(p, '#mapSec');
  await shot(p, { id: 'SC-04.02-2', fe: 'FE-04.02', title: 'Labels on the map', caption: 'On the map, red labels show cleaning within 7 days. White dashed labels show rules that do not apply soon.', frs: ['FR-04.02.001', 'FR-04.02.004', 'FR-04.02.005'] },
    [{ sel: '#map svg', n: 1, text: 'Red and dashed labels', dx: 60, dy: 70 }]);
  await p.context().close();

  // FE-05 Map
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await scrollTo(p, '#mapSec');
  await shot(p, { id: 'SC-05.01-1', fe: 'FE-05.01', title: 'Map of the area', caption: 'The map shows the real streets with names, north at the top and a scale bar. The dot is the parking place.', frs: ['FR-05.01.001', 'FR-05.01.002', 'FR-05.01.003', 'FR-05.01.004'] },
    [{ sel: '#map svg', n: 1, text: 'North', dx: 22, dy: 22 }, { sel: '#map svg', n: 2, text: 'Scale bar', dx: 30, dy: 330 }]);
  await shot(p, { id: 'SC-05.02-1', fe: 'FE-05.02', title: 'Sections in blue and red', caption: 'Blue lines allow parking at the start time. Red lines do not. Grey dotted lines are other parking. A black outline marks the section that the result uses.', frs: ['FR-05.02.001', 'FR-05.02.002', 'FR-05.02.003', 'FR-05.02.004', 'FR-05.02.005'] },
    [{ sel: '#map svg', n: 1, text: 'Map lines', dx: 180, dy: 200 }]);
  await p.click('#zin'); await p.waitForTimeout(250);
  await shot(p, { id: 'SC-05.03-1', fe: 'FE-05.03', title: 'Labels after zoom', caption: 'The user zooms in. Each M section in view gets its own label with a line to the section.', frs: ['FR-05.03.002', 'FR-05.03.003', 'FR-05.03.006'] },
    [{ sel: '#zin', n: 1, text: 'Zoom in' }]);
  await shot(p, { id: 'SC-05.04-1', fe: 'FE-05.04', title: 'Zoom and move', caption: 'The user zooms with two fingers or the + and − buttons, and moves the map with one finger. The ◎ button returns to the parking place.', frs: ['FR-05.04.001', 'FR-05.04.002', 'FR-05.04.003'] },
    [{ sel: '#zin', n: 1, text: '+' }, { sel: '#zout', n: 2, text: '−' }, { sel: '#zreset', n: 3, text: 'Back to parking place' }]);
  await scrollTo(p, '.legend', 20);
  await shot(p, { id: 'SC-05.05-1', fe: 'FE-05.05', title: 'Legend', caption: 'The legend below the map explains each line, dot and label type in words.', frs: ['FR-05.05.001', 'FR-05.05.002'] },
    [{ sel: '.legend', n: 1, text: 'Legend' }]);
  await p.context().close();

  // FE-06 Longest stays nearby
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await scrollTo(p, '#sugSec');
  await shot(p, { id: 'SC-06.01-1', fe: 'FE-06.01', title: 'Longest stays nearby', caption: 'The list shows M sections within 500 m, longest stay first. Each bar shows the stay, where a full bar is 14 days.', frs: ['FR-06.01.001', 'FR-06.01.002', 'FR-06.01.005', 'FR-06.01.006'] },
    [{ sel: '#sug .sg:nth-child(1) .sg-top', n: 1, text: 'Street and numbers' }, { sel: '#sug .sg:nth-child(1) .sg-dur', n: 2, text: 'Stay length' }, { sel: '#sug .sg:nth-child(1) .sg-bar', n: 3, text: 'Bar' }, { sel: '#sug .sg:nth-child(1) .sg-meta', n: 4, text: 'Sign, end, distance' }]);
  await p.click('#sug .sg:nth-child(1)'); await p.waitForTimeout(700); await scrollTo(p, '#mapSec');
  await shot(p, { id: 'SC-06.02-1', fe: 'FE-06.02', title: 'Suggestion on the map', caption: 'The user taps a suggestion. The app scrolls to the map, moves the map to the section and outlines it in black and white.', frs: ['FR-06.02.001', 'FR-06.02.002'] },
    [{ sel: '#map svg', n: 1, text: 'Outlined suggestion', dx: 170, dy: 160 }]);
  await p.context().close();

  // FE-07.01 Use my location (real capture with a simulated position) + mock-up of the permission prompt
  p = await newPage(b, { geo: { latitude: 57.69376, longitude: 11.95425 } });
  await p.evaluate(() => { const $ = id => document.getElementById(id); $('street').value = ''; $('num').value = ''; scrollTo(0, 0); });
  await mockOverlay(p, `<div class="mk-dim"></div><div class="mk-dlg"><div style="text-align:center;font-size:26px">⌖</div><h3>Allow M4 Parking to access this device's location?</h3>
    <span class="opt">While using the app</span><span class="opt">Only this time</span><span class="opt">Don't allow</span></div>`, DLG_CSS);
  await shot(p, { id: 'SC-07.01-1', fe: 'FE-07.01', mock: true, title: 'Location permission (mock-up)', caption: 'The user taps Use my location for the first time. Android asks for permission. The user allows it.', frs: ['FR-07.01.001', 'FR-07.01.005'] },
    [{ sel: '.mk-dlg .opt', n: 1, text: 'Allow' }]);
  await p.context().close();
  p = await newPage(b, { geo: { latitude: 57.69376, longitude: 11.95425 } });
  await p.click('#gpsBtn'); await p.waitForTimeout(600); await p.evaluate(() => scrollTo(0, 0)); await scrollTo(p, '#f', 70);
  await shot(p, { id: 'SC-07.01-2', fe: 'FE-07.01', title: 'Address from the position', caption: 'The app fills in the nearest M-zone address, Sveagatan 12, and shows the distance and the accuracy. Then it checks the address.', frs: ['FR-07.01.002', 'FR-07.01.003'] },
    [{ sel: '#gpsBtn', n: 1, text: 'Use my location' }, { sel: '#gpsMsg', n: 2, text: 'Distance and accuracy' }, { sel: '#street', n: 3, text: 'Filled in' }]);
  await p.context().close();

  // FE-08 My car and payment
  p = await newPage(b);
  await check(p, 'Linnégatan', '40'); await scrollTo(p, '#parkBtn', 420);
  await shot(p, { id: 'SC-08.01-1', fe: 'FE-08.01', title: 'I parked here', caption: 'The permit is valid at Linnégatan 40. The user parks and taps "I parked here".', frs: ['FR-08.01.001'] },
    [{ sel: '#parkBtn', n: 1, text: 'I parked here' }]);
  await p.click('#parkBtn'); await p.waitForTimeout(500); await p.evaluate(() => scrollTo(0, 0)); await scrollTo(p, '#carSec');
  await shot(p, { id: 'SC-08.01-2', fe: 'FE-08.01', title: 'My car card', caption: 'The app saves the car and shows the My car card below the week banner. "I moved the car" deletes it.', frs: ['FR-08.01.002', 'FR-08.01.003', 'FR-08.01.004'] },
    [{ sel: '.carhead .s-title', n: 1, text: 'Saved address' }, { sel: '#moved', n: 2, text: 'I moved the car' }]);
  await shot(p, { id: 'SC-08.02-1', fe: 'FE-08.02', title: 'Free time, then pay or move', caption: 'Free time ends at 09:00. Then the user can pay Taxa 1 until 18:00, when the night sign covers the place again.', frs: ['FR-08.02.001', 'FR-08.02.002', 'FR-08.02.003', 'FR-08.02.006', 'FR-08.02.007', 'FR-08.02.008', 'FR-08.02.009'] },
    [{ sel: '#car .step:nth-child(2) .s-big', n: 1, text: 'Free until' }, { sel: '#car .step:nth-child(3) .s-big', n: 2, text: 'Pay or move' }, { sel: '#car .step:nth-child(3) .kv', n: 3, text: 'Taxa, price, max time' }]);
  await scrollTo(p, '#car .payrow', 260);
  await shot(p, { id: 'SC-08.03-1', fe: 'FE-08.03', title: 'Payment buttons', caption: 'The card has three buttons. The user taps "Open Parkering Göteborg" to pay in that app.', frs: ['FR-08.03.001', 'FR-08.04.001', 'FR-08.04.005', 'FR-08.04.003', 'FR-08.04.004'] },
    [{ sel: '#car .paybtn', n: 1, text: 'Open Parkering Göteborg' }, { sel: '#car [data-act="sms"]', n: 2, text: 'Pay by SMS' }, { sel: '#car [data-act="stop"]', n: 3, text: 'Stop SMS parking' }, { sel: '#car .payrow + .hint', n: 4, text: 'Check platskod' }]);
  await p.context().close();
  // card variant: move (street cleaning)
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await p.click('#parkBtn'); await p.waitForTimeout(400); await scrollTo(p, '#carSec');
  await shot(p, { id: 'SC-08.02-2', fe: 'FE-08.02', title: 'Move for street cleaning', caption: 'At Sveagatan 12, street cleaning ends the free time. Street cleaning cannot be paid for, so the card tells the user to move the car.', frs: ['FR-08.02.004'] },
    [{ sel: '#car .step:nth-child(3) .s-big', n: 1, text: 'Move the car' }, { sel: '#car .step:nth-child(3) .ban', n: 2, text: 'Cleaning rule' }]);
  await p.context().close();

  // mock-ups: Parkering Göteborg app, SMS app, notification
  p = await mockPage(b, `<div style="padding:40px 24px;text-align:center">
    <div style="margin:60px auto 24px;width:96px;height:96px;border-radius:22px;background:#d9dde3;display:flex;align-items:center;justify-content:center;font:700 14px system-ui;color:#555">App icon</div>
    <div style="font:700 22px system-ui">Parkering Göteborg</div>
    <p style="color:#555;margin:18px 0 30px">The Parkering Göteborg app opens on its start screen. The user selects the parking area and starts the parking there.</p>
    <div style="border:2px dashed #999;border-radius:12px;padding:16px;color:#555;text-align:left">This mock-up shows only that the other app opens. It does not show the real design of the Parkering Göteborg app.</div></div>`);
  await mockOverlay(p, '');
  await shot(p, { id: 'SC-08.03-2', fe: 'FE-08.03', mock: true, title: 'Parkering Göteborg opens (mock-up)', caption: 'The Parkering Göteborg app opens. The user starts and approves the payment in that app.', frs: ['FR-08.03.001', 'FR-08.03.003'] }, []);
  await p.context().close();
  p = await mockPage(b, `<div style="background:#fff;padding:14px 16px;border-bottom:1px solid #ddd;display:flex;gap:14px;align-items:center"><span style="font-size:22px">←</span><div><div style="font-weight:700">72430</div><div style="font-size:13px;color:#666">SMS</div></div></div>
    <div style="height:640px"></div>
    <div style="position:absolute;left:0;right:0;top:730px;padding:12px;background:#fff;border-top:1px solid #ddd;display:flex;gap:10px;align-items:center">
      <div id="msg" style="flex:1;border:1px solid #bbb;border-radius:22px;padding:12px 16px;font-size:17px">801</div>
      <div id="send" style="width:48px;height:48px;border-radius:50%;background:#0b5cad;color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px">➤</div></div>`);
  await mockOverlay(p, '');
  await shot(p, { id: 'SC-08.04-1', fe: 'FE-08.04', mock: true, title: 'SMS ready to send (mock-up)', caption: 'The SMS app opens with the number 72430 and the message 801. The user compares the code with the sign, then taps Send.', frs: ['FR-08.04.001', 'FR-08.04.002'] },
    [{ sel: '#msg', n: 1, text: 'Platskod 801' }, { sel: '#send', n: 2, text: 'Send' }]);
  await p.context().close();
  p = await mockPage(b, `<div style="background:#1b2430;color:#fff;height:${H}px;padding-top:20px">
    <div style="padding:10px 18px;font-size:13px;opacity:.8">Tuesday 17 November</div>
    <div id="nt" style="margin:10px 12px;background:#2a3544;border-radius:18px;padding:14px 16px">
      <div style="font-size:12px;opacity:.75;margin-bottom:4px">M4 Parking · 08:45</div>
      <div style="font-weight:700">Free parking ends 09:00 · Linnégatan 40</div>
      <div style="font-size:14px;opacity:.9;margin-top:4px">Pay Taxa 1 (platskod 801) until 18:00, or move the car.</div>
      <div style="display:flex;gap:18px;margin-top:12px;font-weight:700;color:#8cc4ff"><span id="a1">OPEN PARKERING GÖTEBORG</span><span id="a2">PAY BY SMS</span></div></div></div>`);
  await mockOverlay(p, '');
  await shot(p, { id: 'SC-08.05-1', fe: 'FE-08.05', mock: true, title: 'Reminder (mock-up)', caption: 'At 08:45, 15 minutes before free time ends, the Android app shows a reminder with two buttons.', frs: ['FR-08.05.001', 'FR-08.05.003'] },
    [{ sel: '#nt', n: 1, text: 'Reminder' }, { sel: '#a1', n: 2, text: 'Open Parkering Göteborg' }, { sel: '#a2', n: 3, text: 'Pay by SMS' }]);
  await p.context().close();
  p = await newPage(b);
  await check(p, 'Linnégatan', '40'); await p.click('#parkBtn'); await p.waitForTimeout(400); await scrollTo(p, '#car > .hint', 600);
  await shot(p, { id: 'SC-08.05-2', fe: 'FE-08.05', title: 'Reminder note in the web app', caption: 'In the web app, the card tells the user that reminders work only in the Android app.', frs: ['FR-08.05.008'] },
    [{ sel: '#car > .hint', n: 1, text: 'Reminder note' }]);
  await p.context().close();

  // FE-09.05 data date in the footer
  p = await newPage(b);
  await check(p, 'Sveagatan', '12'); await p.evaluate(() => scrollTo(0, document.body.scrollHeight));
  await shot(p, { id: 'SC-09.05-1', fe: 'FE-09.05', title: 'Data date', caption: 'The bottom of the app shows the data sources, the number of M sections and streets, and the download date.', frs: ['FR-09.05.001'] },
    [{ sel: '#dataNote', n: 1, text: 'Data date and counts' }]);
  await p.context().close();

  // FE-10 Distribution (mock-ups of browser and installer screens)
  p = await mockPage(b, `<div style="background:#fff;margin:8px;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.25);position:absolute;right:8px;top:40px;width:250px;padding:6px 0;font-size:15px">
    ${['New tab', 'Bookmarks', 'History', 'Downloads', 'Share…', 'Find in page', 'Add to Home screen', 'Desktop site', 'Settings'].map(t => `<div ${t === 'Add to Home screen' ? 'id="a2hs" style="padding:12px 18px;background:#e8eefc;font-weight:700"' : 'style="padding:12px 18px"'}>${t}</div>`).join('')}</div>
    <div style="padding:12px 16px;background:#fff;border-bottom:1px solid #ddd;font-size:14px">marwa112.github.io/m4-parking <span id="menu" style="float:right;font-size:18px">⋮</span></div>`);
  await mockOverlay(p, '');
  await shot(p, { id: 'SC-10.01-1', fe: 'FE-10.01', mock: true, title: 'Add to Home screen (mock-up)', caption: 'The user opens the web address in Chrome, taps the ⋮ menu and taps "Add to Home screen".', frs: ['FR-10.01.001', 'FR-10.01.002'] },
    [{ sel: '#menu', n: 1, text: 'Menu' }, { sel: '#a2hs', n: 2, text: 'Add to Home screen' }]);
  await p.context().close();
  p = await mockPage(b, `<div style="position:absolute;inset:28px 0 0;background:rgba(0,0,0,.45)"></div>
    <div style="position:absolute;left:24px;right:24px;top:300px;background:#fff;border-radius:22px;padding:22px">
      <div style="font:700 18px system-ui;margin-bottom:8px">M4 Parking</div><div>Do you want to install this app?</div>
      <div style="display:flex;justify-content:flex-end;gap:26px;margin-top:22px;font-weight:700;color:#0b3d91"><span>Cancel</span><span id="inst">Install</span></div></div>`);
  await mockOverlay(p, '');
  await shot(p, { id: 'SC-10.02-1', fe: 'FE-10.02', mock: true, title: 'Install the APK (mock-up)', caption: 'The user opens the downloaded file m4-parking.apk. Android asks to install M4 Parking. The user taps Install.', frs: ['FR-10.02.002'] },
    [{ sel: '#inst', n: 1, text: 'Install' }]);
  await p.context().close();

  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 1));
  console.log('screens:', manifest.screens.length, 'mock-ups:', manifest.screens.filter(s => s.mock).length);
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
