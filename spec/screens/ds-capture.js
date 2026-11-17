// Captures the design system: one image per element plus its measured style values,
// in light and dark mode, straight from the running app (Figma-style "inspect" data).
//
// Usage (from the repository root, web app served on http://localhost:8765/):
//   DS_VERSION=0.3 FONT_DIR=.../@fontsource node spec/screens/ds-capture.js
// Writes docs/spec/design/v<version>/DS-*.png and ds.json. Never overwrites a version.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const VERSION = process.env.DS_VERSION || '0.3';
const OUT = path.join(ROOT, 'docs', 'spec', 'design', 'v' + VERSION);
const URL = process.env.APP_URL || 'http://localhost:8765/';
const BASE = '2026-11-17T08:45:00';
if (fs.existsSync(OUT)) { console.error(`${OUT} exists. A version is never overwritten.`); process.exit(1); }
fs.mkdirSync(OUT, { recursive: true });

let fontCss = '';
if (process.env.FONT_DIR) {
  const ff = (fam, file, w) => `@font-face{font-family:'${fam}';font-weight:${w};src:url(data:font/woff2;base64,${fs.readFileSync(path.join(process.env.FONT_DIR, file)).toString('base64')}) format('woff2')}`;
  fontCss = [400, 600, 800, 900].map(w => ff('Overpass', `overpass/files/overpass-latin-${w}-normal.woff2`, w)).join('') +
    [500, 700].map(w => ff('Overpass Mono', `overpass-mono/files/overpass-mono-latin-${w}-normal.woff2`, w)).join('');
}

// Each element: how to reach the state, which node to crop, and which parts to inspect.
const ELEMENTS = [
  { id: 'DS-CMP-01', name: 'Header', go: ['Sveagatan', '12'], sel: 'header', parts: [['Title', 'h1'], ['Permit chip', '.permit']] },
  { id: 'DS-CMP-02', name: 'Section card', go: ['Sveagatan', '12'], sel: 'section[aria-label="Week number"]', parts: [['Card', 'section[aria-label="Week number"]']] },
  { id: 'DS-CMP-03', name: 'Week banner', go: ['Sveagatan', '12'], sel: 'section[aria-label="Week number"] .week', parts: [['Week number', '#wkNum'], ['Odd week pill (filled)', '#wkPill'], ['Next week line', '#wkNext']] },
  { id: 'DS-CMP-04', name: 'Section heading', go: ['Sveagatan', '12'], sel: '#sugSec h2', parts: [['Heading', '#sugSec h2']] },
  { id: 'DS-CMP-05', name: 'Text field with label', go: ['Sveagatan', '12'], sel: '#f > div:first-child', parts: [['Label', '#f > div:first-child label'], ['Input', '#street']] },
  { id: 'DS-CMP-06', name: 'Primary button', go: ['Sveagatan', '12'], sel: '.go', parts: [['Button', '.go']] },
  { id: 'DS-CMP-07', name: 'Secondary button', go: ['Sveagatan', '12'], sel: '#nowBtn', parts: [['Button', '#nowBtn']] },
  { id: 'DS-CMP-08', name: 'Verdict card: allowed', go: ['Sveagatan', '12'], sel: '#steps .step:nth-child(2)', parts: [['Card', '#steps .step:nth-child(2)'], ['Mark', '#steps .step:nth-child(2) .mark'], ['Verdict', '#steps .step:nth-child(2) .s-big'], ['Detail', '#steps .step:nth-child(2) .s-sub']] },
  { id: 'DS-CMP-09', name: 'Verdict card: not allowed', go: ['Seminariegatan', '10', '2026-11-17T10:30'], sel: '#steps .step:nth-child(2)', parts: [['Card', '#steps .step:nth-child(2)'], ['Mark', '#steps .step:nth-child(2) .mark'], ['Verdict', '#steps .step:nth-child(2) .s-big']] },
  { id: 'DS-CMP-10', name: 'Info card', go: ['Linnégatan', '8'], sel: '#steps .step.info', parts: [['Card', '#steps .step.info'], ['Mark', '#steps .step.info .mark'], ['Title', '#steps .step.info .s-title']] },
  { id: 'DS-CMP-11', name: 'Key–value list', go: ['Sveagatan', '12'], sel: '#steps .kv', parts: [['Key', '#steps .kv dt'], ['Value', '#steps .kv dd']] },
  { id: 'DS-CMP-12', name: 'Cleaning badge: soon', go: ['Sveagatan', '12'], sel: '#steps .kv .ban', parts: [['Badge', '#steps .kv .ban']] },
  { id: 'DS-CMP-13', name: 'Cleaning badge: later', go: ['Sveagatan', '3'], sel: '#steps .kv .ban.cold', parts: [['Badge', '#steps .kv .ban.cold']] },
  { id: 'DS-CMP-14', name: 'Suggestion row with bar', go: ['Sveagatan', '12'], sel: '#sug .sg', parts: [['Row', '#sug .sg'], ['Street', '#sug .sg .sg-top'], ['Stay', '#sug .sg .sg-dur'], ['Bar track', '#sug .sg .sg-bar'], ['Bar fill', '#sug .sg .sg-bar span'], ['Details', '#sug .sg .sg-meta']] },
  { id: 'DS-CMP-15', name: 'Legend', go: ['Sveagatan', '12'], sel: '.legend', parts: [['Item', '.legend > span']] },
  { id: 'DS-CMP-16', name: 'Hint and note text', go: ['linne gatan', '40'], sel: '#fuzzy', parts: [['Note', '#fuzzy']] },
  { id: 'DS-CMP-17', name: 'My car header', park: ['Linnégatan', '40'], sel: '.carhead', parts: [['Address', '.carhead .s-title'], ['Parked line', '.carhead .s-sub'], ['Button', '#moved']] },
  { id: 'DS-CMP-18', name: 'Pay buttons', park: ['Linnégatan', '40'], sel: '#car .payrow', parts: [['Pay button', '#car .paybtn'], ['Link button', '#car .lnk']] },
  { id: 'DS-CMP-19', name: 'Map with labels', go: ['Sveagatan', '12'], zoom: 1, sel: '#mapbox', parts: [['Map frame', '#mapbox'], ['Zoom button', '#zin']] },
];

// Interactive elements: one image per state, from the real app. Disabled is set on the element
// to show how the browser draws it today (the app defines no own disabled style yet).
const STATES = [
  { id: 'DS-CMP-06', sel: '.go', go: ['Sveagatan', '12'] },
  { id: 'DS-CMP-07', sel: '#nowBtn', go: ['Sveagatan', '12'] },
  { id: 'DS-CMP-05', sel: '#street', go: ['Sveagatan', '12'] },
  { id: 'DS-CMP-20', sel: '#when', go: ['Sveagatan', '12'], name: 'Date and time field' },
  { id: 'DS-CMP-14', sel: '#sug .sg', go: ['Sveagatan', '12'] },
  { id: 'DS-CMP-18', sel: '#car .paybtn', park: ['Linnégatan', '40'] },
  { id: 'DS-CMP-21', sel: '#zin', go: ['Sveagatan', '12'], name: 'Map zoom button' },
  { id: 'DS-CMP-22', sel: '#gpsBtn', go: ['Sveagatan', '12'], name: 'Location button' },
];
const SPROPS = ['backgroundColor', 'color', 'borderColor', 'borderWidth', 'outline', 'outlineOffset', 'boxShadow', 'opacity', 'cursor', 'transform'];
const PROPS = ['width', 'height', 'padding', 'border', 'borderRadius', 'backgroundColor', 'backgroundImage', 'color', 'fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'textTransform', 'gap', 'boxShadow'];

async function page(b, scheme, time = BASE) {
  const ctx = await b.newContext({ viewport: { width: 412, height: 892 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, colorScheme: scheme });
  if (fontCss) await ctx.route('**/fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: fontCss }));
  await ctx.route('**/marwa112.github.io/**', r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date(time));
  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.waitForFunction(() => document.querySelectorAll('#sug .sg').length > 0);
  return p;
}
async function setState(p, e) {
  const [s, n, w] = e.go || e.park;
  await p.evaluate(([s, n, w]) => {
    const $ = id => document.getElementById(id);
    $('street').value = s; $('num').value = n;
    if (w) { $('when').value = w; $('when').dispatchEvent(new Event('input')); } else $('nowBtn').click();
    $('until').value = ''; $('f').requestSubmit();
  }, [s, n, w]);
  await p.waitForTimeout(300);
  if (e.park) { await p.click('#parkBtn'); await p.waitForTimeout(300); }
  if (e.zoom) { await p.evaluate(() => document.getElementById('mapSec').scrollIntoView()); await p.click('#zin'); await p.waitForTimeout(250); }
}
async function inspect(p, e) {
  return p.evaluate(([e, PROPS]) => {
    const root = document.querySelector(e.sel); const rb = root.getBoundingClientRect();
    const read = el => { const c = getComputedStyle(el), b = el.getBoundingClientRect(), o = {};
      for (const k of PROPS) o[k] = c[k];
      o.width = Math.round(b.width) + 'px'; o.height = Math.round(b.height) + 'px';
      o.box = [(b.left - rb.left) / rb.width * 100, (b.top - rb.top) / rb.height * 100, b.width / rb.width * 100, b.height / rb.height * 100].map(v => +v.toFixed(2));
      o.offset = [Math.round(b.left - rb.left), Math.round(b.top - rb.top)];
      return o; };
    return { root: read(root), parts: e.parts.map(([label, sel]) => { const el = document.querySelector(sel); return el ? { label, sel, ...read(el) } : { label, sel, missing: true }; }) };
  }, [e, PROPS]);
}

(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const out = { version: VERSION, elements: [], tokens: {} };
  // tokens: CSS custom properties, light and dark
  for (const scheme of ['light', 'dark']) {
    const p = await page(b, scheme);
    out.tokens[scheme] = await p.evaluate(() => { const c = getComputedStyle(document.documentElement), o = {};
      for (const k of ['--bg', '--surface', '--ink', '--muted', '--line', '--sign', '--ok', '--ok-soft', '--no', '--no-soft', '--stop', '--ban-bg', '--ban-fg', '--road', '--road-major', '--halo', '--pin', '--other', '--f-display', '--f-mono']) o[k] = c.getPropertyValue(k).trim();
      return o; });
    await p.context().close();
  }
  for (const e of ELEMENTS) {
    const rec = { id: e.id, name: e.name, file: `${e.id}.png`, light: null, dark: null };
    for (const scheme of ['light', 'dark']) {
      const p = await page(b, scheme, e.go && e.go[2] ? e.go[2] : BASE);
      await setState(p, e);
      const el = await p.$(e.sel);
      if (!el) { console.warn('missing', e.id, scheme); await p.context().close(); continue; }
      await el.scrollIntoViewIfNeeded();
      const pad = e.id === 'DS-CMP-02' ? 0 : 6;
      const bb = await el.boundingBox();
      const clip = { x: Math.max(0, bb.x - pad), y: Math.max(0, bb.y - pad), width: Math.min(412 - Math.max(0, bb.x - pad), bb.width + 2 * pad), height: bb.height + 2 * pad };
      await p.screenshot({ path: path.join(OUT, `${e.id}${scheme === 'dark' ? '-dark' : ''}.png`), clip });
      rec[scheme] = await inspect(p, e);
      rec[scheme].pad = pad;
      await p.context().close();
    }
    out.elements.push(rec);
    console.log(e.id, e.name);
  }
  // states
  out.states = [];
  for (const st of STATES) {
    const rec = { id: st.id, name: st.name || null, states: [] };
    for (const state of ['default', 'hover', 'focus', 'pressed', 'disabled']) {
      const p = await page(b, 'light');
      await setState(p, st);
      const el = await p.$(st.sel);
      if (!el) { console.warn('missing', st.id); await p.context().close(); continue; }
      await el.scrollIntoViewIfNeeded();
      const bb = await el.boundingBox();
      let note = '';
      if (state === 'hover') await p.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
      if (state === 'focus') { await p.keyboard.press('Tab'); await p.keyboard.press('Shift+Tab'); await el.focus(); await p.keyboard.press('Shift'); }
      if (state === 'pressed') { await p.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2); await p.mouse.down(); }
      if (state === 'disabled') {
        note = await p.evaluate(sel => { const e = document.querySelector(sel); if ('disabled' in e) { e.disabled = true; return ''; } e.setAttribute('aria-disabled', 'true'); return 'Not possible on a link'; }, st.sel);
      }
      await p.waitForTimeout(120);
      const pad = 8;
      const clip = { x: Math.max(0, bb.x - pad), y: Math.max(0, bb.y - pad), width: Math.min(412 - Math.max(0, bb.x - pad), bb.width + 2 * pad), height: bb.height + 2 * pad };
      const file = `${st.id}-state-${state}.png`;
      await p.screenshot({ path: path.join(OUT, file), clip });
      const css = await p.evaluate(([sel, P]) => { const c = getComputedStyle(document.querySelector(sel)), o = {}; for (const k of P) o[k] = c[k]; return o; }, [st.sel, SPROPS]);
      if (state === 'pressed') await p.mouse.up();
      rec.states.push({ state, file, css, note });
      await p.context().close();
    }
    out.states.push(rec);
    console.log('states', st.id);
  }
  fs.writeFileSync(path.join(OUT, 'ds.json'), JSON.stringify(out, null, 1));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
