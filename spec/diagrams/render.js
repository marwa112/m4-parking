// Renders spec/diagrams/*.mmd to static SVG files for the specification.
//
// Usage (from the repository root):
//   DIAGRAMS_VERSION=0.3 MERMAID_JS=/path/to/mermaid/dist/mermaid.min.js node spec/diagrams/render.js
//
// Writes docs/spec/diagrams/v<version>/*.svg. It never overwrites an existing version folder.
// Colours: blue, orange and grey only (no red/green pairs), text on every shape.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const VERSION = process.env.DIAGRAMS_VERSION || '0.3';
const OUT = path.join(ROOT, 'docs', 'spec', 'diagrams', 'v' + VERSION);
const SRC = __dirname;
const MERMAID = process.env.MERMAID_JS || require.resolve('mermaid/dist/mermaid.min.js');

if (fs.existsSync(OUT)) { console.error(`${OUT} exists. A version is never overwritten.`); process.exit(1); }

const theme = {
  startOnLoad: false, securityLevel: 'strict', theme: 'base',
  fontFamily: 'Arial, Helvetica, sans-serif',
  themeVariables: {
    fontFamily: 'Arial, Helvetica, sans-serif', fontSize: '15px',
    primaryColor: '#e8f0fa', primaryBorderColor: '#0b5cad', primaryTextColor: '#121a24',
    secondaryColor: '#fde6c4', secondaryBorderColor: '#9a4a00', secondaryTextColor: '#121a24',
    tertiaryColor: '#f3f5f8', tertiaryBorderColor: '#7a8696', tertiaryTextColor: '#121a24',
    lineColor: '#3f4b5a', textColor: '#121a24', clusterBkg: '#f7f9fc', clusterBorder: '#9aa7b6',
    edgeLabelBackground: '#ffffff', noteBkgColor: '#fde6c4', noteBorderColor: '#9a4a00',
    actorBkg: '#e8f0fa', actorBorder: '#0b5cad', signalColor: '#3f4b5a', labelBoxBkgColor: '#fde6c4',
    altSectionBkgColor: '#f7f9fc',
  },
  htmlLabels: false,
  flowchart: { htmlLabels: false, curve: 'basis', padding: 12, nodeSpacing: 40, rankSpacing: 50 },
  sequence: { mirrorActors: false, actorMargin: 40, messageMargin: 32 },
};

(async () => {
  const files = fs.readdirSync(SRC).filter(f => f.endsWith('.mmd')).sort();
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  const p = await b.newPage();
  await p.setContent('<!doctype html><html><body></body></html>');
  await p.addScriptTag({ content: fs.readFileSync(MERMAID, 'utf8') });
  await p.evaluate(cfg => window.mermaid.initialize(cfg), theme);
  fs.mkdirSync(OUT, { recursive: true });
  for (const f of files) {
    const src = fs.readFileSync(path.join(SRC, f), 'utf8');
    const id = f.replace('.mmd', '').replace(/[^A-Za-z0-9]/g, '_');
    const svg = await p.evaluate(async ([id, src]) => (await window.mermaid.render(id, src)).svg, [id, src]);
    fs.writeFileSync(path.join(OUT, f.replace('.mmd', '.svg')), svg);
    console.log(f, svg.length);
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
