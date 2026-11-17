// Builds twostream_talk.pptx: a plain, simple deck. Slide titles, bullets, the setup table and
// speaker notes are read straight from content.md, so editing content.md and re-running this
// script is all it takes to update the talk.
// Run from this folder:  node build_deck.js   (needs pptxgenjs; set NODE_PATH if installed elsewhere)
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const OUT = process.env.DECK_OUT || path.join(HERE, "twostream_talk.pptx");   // DECK_OUT: test builds elsewhere
const md = fs.readFileSync(path.join(HERE, "content.md"), "utf8");

// Quiet-start figures: use the full-run set once content.md describes the full run
// (job 11093069); until then use the short smoke-run set that matches content.md's numbers.
const QUIET = /11093069/.test(md) ? "" : "quiet_smoke/";
const FIG = (f) => path.join(HERE, "figures", f);
const QFIG = (f) => FIG(QUIET + f);
const SRC = (f) => path.join(HERE, "assets", "sourced", f);

// ---- read content.md --------------------------------------------------------
// Sections start with "## Slide N: Title" or "## BN: Title"; each has **Bullets**, optional
// **Table**, and **Speaker notes** blocks. "## Likely Q&A" holds **Qn. question** paragraphs.
function parseSections(text) {
  const out = {};
  const parts = text.split(/\n(?=## )/);
  for (const part of parts) {
    const m = part.match(/^## (Slide (\d+)|B(\d+)): (.*)/);
    if (!m) continue;
    const key = m[2] ? `S${m[2]}` : `B${m[3]}`;
    const lines = part.split("\n");
    const sec = { title: m[4].trim(), bullets: [], table: [], notes: "" };
    let mode = null; const notes = [];
    for (const raw of lines.slice(1)) {
      const line = raw.trimEnd();
      if (/^\*\*Bullets\*\*/.test(line)) { mode = "b"; continue; }
      if (/^\*\*Table\*\*/.test(line)) { mode = "t"; continue; }
      if (/^\*\*Speaker notes\*\*/.test(line)) { mode = "n"; continue; }
      if (/^\*\*(Figure|Title options)/.test(line) || /^---/.test(line)) { mode = null; continue; }
      if (mode === "b" && line.startsWith("- ")) sec.bullets.push(line.slice(2));
      else if (mode === "b" && /^\s+\S/.test(line) && sec.bullets.length) sec.bullets.push("@ " + line.trim());
      if (mode === "t" && line.startsWith("|") && !/^\|[-| ]+\|$/.test(line)) {
        sec.table.push(line.split("|").slice(1, -1).map((c) => c.trim()));
      }
      if (mode === "n" && line.trim()) notes.push(line.trim());
    }
    sec.notes = notes.join(" ");
    if (sec.table.length) sec.table = sec.table.slice(1); // drop the header row
    out[key] = sec;
  }
  return out;
}
function parseQA(text) {
  const i = text.indexOf("## Likely Q&A");
  if (i < 0) return "";
  return text.slice(i).split("\n").slice(1).join("\n").trim()
    .replace(/\*\*(Q\d+\.[^*]*)\*\*\n/g, "$1 ").replace(/\n(?!\n)/g, " ").replace(/\n\n+/g, "\n\n");
}
const RAW = parseSections(md);
const num = (k) => +k.slice(1);
let MAIN = Object.keys(RAW).filter((k) => k[0] === "S").sort((a, b) => num(a) - num(b));
let BACK = Object.keys(RAW).filter((k) => k[0] === "B").sort((a, b) => num(a) - num(b));
// The user chose (2026-11-17) to keep "one time step in detail" in the main talk, right after
// "the loop", even though content.md lists it as a backup. Once content.md has it as a main slide
// this does nothing.
const PROMOTE = { title: /one time step in detail/i, after: /the loop/i };
if (!MAIN.some((k) => PROMOTE.title.test(RAW[k].title))) {
  const b = BACK.find((k) => PROMOTE.title.test(RAW[k].title));
  const a = MAIN.findIndex((k) => PROMOTE.after.test(RAW[k].title));
  if (b && a >= 0) { BACK = BACK.filter((k) => k !== b); MAIN.splice(a + 1, 0, b); }
}
// Renumber "slide N" and "BN" references in content.md's text to the deck's final order.
const slideNo = {}; MAIN.forEach((k, i) => { if (k[0] === "S") slideNo[num(k)] = i + 1; });
const backNo = {}; BACK.forEach((k, i) => { backNo[num(k)] = i + 1; });
const promotedB = MAIN.filter((k) => k[0] === "B").map(num);
const renum = (t) => t
  .replace(/\b([Ss]lides?) (\d+)(\s*[–-]\s*)?(\d+)?/g, (m, w, a, dash, b) =>
    `${w} ${slideNo[+a] ?? a}${b ? (dash || "–") + (slideNo[+b] ?? b) : ""}`)
  .replace(/\b(?:([Bb]ackup) )?B(\d+)\b/g, (m, w, n) => promotedB.includes(+n)
    ? `slide ${MAIN.indexOf("B" + n) + 1}` : `${w ? w + " " : ""}B${backNo[+n] ?? n}`);
const S = {};
for (const [k, sec] of Object.entries(RAW)) {
  S[k] = { ...sec, bullets: sec.bullets.map(renum), notes: renum(sec.notes),
    table: sec.table.map((r) => r.map(renum)) };
}
const QA = renum(parseQA(md));
const need = (k) => { if (!S[k]) throw new Error(`content.md has no section ${k}`); return S[k]; };

// ---- plain style --------------------------------------------------------------
const FONT = "Arial";
const INK = "000000", GREY = "555555", W = 13.333, H = 7.5, MX = 0.6;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Watching an Instability Grow";
pres.author = "Harry Wu";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
for (const [name, size] of [["PLAIN", 32], ["PLAIN_BACKUP", 26]]) pres.defineSlideMaster({
  title: name,
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.3, w: W - 2 * MX, h: 0.9,
        fontFace: FONT, fontSize: size, bold: true, color: INK, valign: "middle", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: W - 1.0, y: H - 0.45, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 12, color: GREY,
    align: "right" },
});

// content.md writes math in plain Unicode; turn the bits Arial lacks into real sub/superscripts.
function rich(str, opts = {}) {
  const s = str.replace(/₀/g, "_0").replace(/γ_max/g, "γ_{max}").replace(/ω_pe/g, "ω_{pe}")
    .replace(/10⁻⁴/g, "10^{-4}").replace(/ ∝ /g, " scales as ").replace(/∝/g, "scales as")
    .replace(/\(m\/M\)\^\{1\/3\}/g, "(m/M)^{1/3}");
  const out = []; let buf = "";
  const push = (t, extra = {}) => { if (t) out.push({ text: t, options: { ...opts, ...extra } }); };
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if ((c === "_" || c === "^") && s[i + 1] === "{") {
      const j = s.indexOf("}", i); push(buf); buf = "";
      push(s.slice(i + 2, j), c === "_" ? { subscript: true } : { superscript: true }); i = j;
    } else if (c === "_" && /[a-z0-9]/i.test(s[i + 1] || "")) {
      push(buf); buf = ""; push(s[++i], { subscript: true });
    } else buf += c;
  }
  push(buf);
  return out;
}
// An item starting with "@ " is an equation line: no bullet, indented under the bullet above.
function bulletRuns(items, size) {
  const runs = [];
  items.forEach((t, j) => {
    const eq = t.startsWith("@ ");
    const r = rich(eq ? t.slice(2) : t, { fontSize: size, color: INK });
    // invisible bullet (no-break space) keeps the bullet indent; one level deeper than the text
    if (eq) { r[0].options.bullet = { code: "00A0" }; r[0].options.indentLevel = 1; }
    else r[0].options.bullet = true;
    if (j < items.length - 1) r[r.length - 1].options.breakLine = true;
    runs.push(...r);
  });
  return runs;
}
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function fitBox(file, box) {
  const { w: pw, h: ph } = pngSize(file);
  let w = box.w, h = w / (pw / ph);
  if (h > box.h) { h = box.h; w = h * (pw / ph); }
  return { x: box.x + (box.w - w) / 2, y: box.y, w, h };
}
function caption(slide, text, box, full = false) {
  // At least 6 in wide (or the full slide width for long credit lines), so it doesn't wrap.
  const x = full ? MX : Math.min(box.x, W - MX - 6);
  const y = full ? H - 0.9 : box.y + box.h + 0.05;   // full-width credit lines sit at the slide bottom
  slide.addText(text, { x, y, w: W - MX - x, h: 0.35, align: x < box.x ? "right" : "left",
    fontFace: FONT, fontSize: 12, italic: true, color: GREY, margin: 0, isTextBox: true });
}
const MINE = "Figure: my simulation (Entity PIC code)";
const WARPX = "WarpX documentation (warpx.readthedocs.io), © 2018 The Regents of the University of California, BSD-3-Clause-LBNL license";
// Sources, licenses and download dates of these images: assets/sourced/SOURCES.md

// One slide = title + bullets on the left + optional figure on the right (or a big figure
// with bullets beside it). Keeps every slide the same plain layout.
function slide(sec, { fig, cap, capFull = false, figW = 7.6, figH = 5.3, bulletH = 5.4, bulletSize = 20, textSize = 24, notes, video, master = "PLAIN" } = {}) {
  const s = pres.addSlide({ masterName: master });
  s.addText(rich(sec.title), { placeholder: "title" });
  const top = 1.4;
  if (!fig) {
    s.addText(bulletRuns(sec.bullets, textSize), { x: MX, y: top, w: W - 2 * MX, h: 5.4, fontFace: FONT,
      valign: "top", margin: 0, paraSpaceAfter: 14, isTextBox: true });
  } else {
    const fx = W - MX - figW;
    const box = fitBox(fig, { x: fx, y: top, w: figW, h: figH });
    if (video) {
      s.addMedia({ type: "video", path: video, ...box,
        cover: "data:image/png;base64," + fs.readFileSync(fig).toString("base64") });
    } else {
      s.addImage({ path: fig, ...box, altText: sec.title });
    }
    if (cap) caption(s, cap, box, capFull);
    s.addText(bulletRuns(sec.bullets, bulletSize), { x: MX, y: top, w: fx - MX - 0.3, h: bulletH,
      fontFace: FONT, valign: "top", margin: 0, paraSpaceAfter: 10, isTextBox: true });
  }
  s.addNotes(notes ?? sec.notes);
  return s;
}

// =============================================================================
// Figures and extras, matched to content.md sections by title (robust to renumbering).
const VIDEO_NOTE = " [Movie: click it to play, 15 s, quiet-start run t = 0 to 70/ω_p. Flat beams until about t = 10, growth, then vortices from about t = 27. The last ~3 s (t = 40 to 70) are fast-forwarded 3x, shown only by the time counter; say so. If it doesn't play, talk over the still (t = 0, 20, 33: the last panel is a few plasma periods after growth stops at ~27, when the vortices are fully formed).]";
const Q = ", quiet-start run";
const FIGS = [
  [/^the math/i, { textSize: 20 }],   // text-only, but long: smaller font so it fits
  [/particles and a grid/i, { fig: SRC("warpx_pic_particles_grid.png"), cap: "Figure (cropped): " + WARPX, capFull: true, figW: 4.6 }],
  [/the loop/i, { fig: SRC("warpx_pic_cycle.png"), cap: "Figure: " + WARPX, capFull: true, figW: 7.2 }],
  [/what the electrons do/i, { fig: FIG("phase_space.png"), video: FIG("phase_space.mp4"), cap: MINE + Q + ". Click to play.", figW: 8.2, bulletSize: 18 }],
  [/grows exponentially/i, { fig: QFIG("growth_fastest_mode.png"), cap: MINE + Q, figW: 8.2, bulletSize: 18 }],
  [/grows in place/i, { fig: QFIG("spacetime_Ex.png"), cap: MINE + Q, figW: 8.2, bulletSize: 18 }],
  [/growth-rate curve/i, { fig: QFIG("growth_rate_vs_k.png"), cap: MINE + Q, figW: 8.0, figH: 4.1, bulletH: 4.4, bulletSize: 17, peakTable: true }],
  [/graphical method/i, { fig: FIG("dispersion_stable_unstable.png"), cap: "Figure: Chen's dispersion relation, plotted by me" }],
  [/trapped electrons/i, { fig: FIG("trapping_separatrix.png"), cap: MINE + Q }],
  [/beams flatten/i, { fig: FIG("fv_plateau.png"), cap: MINE + Q }],
  [/starting positions matter/i, { fig: QFIG("gamma_k_quiet_vs_random.png"), cap: MINE + Q }],
  [/random-start numbers/i, { fig: FIG("random_start/growth_rate_vs_k.png"), cap: MINE + ", random-start run" }],
  [/noise made visible/i, { fig: QFIG("spacetime_Ex_normalized.png"), cap: MINE + Q }],
];
const extrasFor = (title) => (FIGS.find(([re]) => re.test(title)) || [null, {}])[1];

// Peak growth rate and where it occurs, theory vs simulation (added at the user's request).
// Theory: Chen, cold symmetric beams. Simulation: box mode m = 7, the box wavelength closest
// to the theory peak; kv0/omega_p uses the same normalization as the figure.
function peakTable(s) {
  const hd = (t) => ({ text: rich(t, { fontSize: 18, bold: true }), options: { fill: { color: "EEEEEE" } } });
  const cell = (t) => ({ text: rich(t, { fontSize: 18 }) });
  s.addTable([
    [hd(""), hd("Maximum growth rate γ_max"), hd("At wavenumber k")],
    [{ text: "Theory (Chen)", options: { bold: true } }, cell("ω_p/(2√2) ≈ 0.354 ω_p"),
      cell("kv_0 = √(3/8) ω_p ≈ 0.612 ω_p  (k ≈ 6.2 ω_p/c)")],
    [{ text: "Simulation", options: { bold: true } }, cell("0.339 ± 0.014 ω_p"),
      cell("kv_0 ≈ 0.624 ω_p  (k ≈ 6.3 ω_p/c), box wave m = 7")],
  ], { x: MX, y: 5.95, w: W - 2 * MX, colW: [2.1, 3.6, W - 2 * MX - 5.7], fontFace: FONT, fontSize: 18,
    color: INK, rowH: 0.34, valign: "middle", margin: [0, 0.08, 0, 0.08],
    border: { type: "solid", color: "999999", pt: 1 } });
}
function titleSlide(sec) {
  const [main, sub] = sec.title.split(/:\s*/, 2);
  const s = pres.addSlide({ masterName: "PLAIN" });
  s.addText(main, { x: MX, y: 2.2, w: W - 2 * MX, h: 1.0, fontFace: FONT, fontSize: 40, bold: true,
    color: INK, align: "center", margin: 0, isTextBox: true });
  if (sub) s.addText(sub, { x: MX, y: 3.25, w: W - 2 * MX, h: 0.6, fontFace: FONT, fontSize: 24,
    color: INK, align: "center", margin: 0, isTextBox: true });
  s.addText(sec.bullets.join("\n"), { x: MX, y: 4.5, w: W - 2 * MX, h: 1.0, fontFace: FONT,
    fontSize: 20, color: GREY, align: "center", margin: 0, isTextBox: true });
  s.addNotes(sec.notes);
}
function setupSlide(sec) {
  const s = pres.addSlide({ masterName: "PLAIN" });
  s.addText(rich(sec.title), { placeholder: "title" });
  s.addText(bulletRuns(sec.bullets, 20), { x: MX, y: 1.3, w: W - 2 * MX, h: 1.6, fontFace: FONT,
    valign: "top", margin: 0, paraSpaceAfter: 6, isTextBox: true });
  const rows = sec.table.map(([a, b]) => [
    { text: a, options: { bold: true } }, { text: rich(b, { fontSize: 18 }) }]);
  s.addTable(rows, { x: MX, y: 3.1, w: W - 2 * MX, colW: [3.0, W - 2 * MX - 3.0], fontFace: FONT,
    fontSize: 18, color: INK, rowH: 0.62, valign: "middle", margin: [0, 0.12, 0, 0.12],
    border: { type: "solid", color: "999999", pt: 1 } });
  s.addNotes(sec.notes);
}

// ---- main talk, in content.md order (plus the promoted slide) ----------------
MAIN.forEach((k, i) => {
  const sec = need(k);
  const last = i === MAIN.length - 1;
  if (i === 0) return titleSlide(sec);
  if (sec.table.length && /setup/i.test(sec.title)) return setupSlide(sec);
  const ex = { ...extrasFor(sec.title) };
  if (ex.video && !fs.existsSync(ex.video)) delete ex.video;
  let notes = sec.notes;
  if (ex.video) notes += VIDEO_NOTE;
  if (last && QA) notes += "\n\n----- Likely Q&A (not part of the talk) -----\n\n" + QA;   // after the spoken part
  const s = slide(sec, { ...ex, notes });
  if (ex.peakTable) peakTable(s);
});

// ---- backups: same plain layout, "Backup BN:" in the title --------------------
BACK.forEach((k, i) => {
  const sec = { ...need(k), title: `Backup B${i + 1}: ${need(k).title}` };
  slide(sec, { bulletSize: 18, figW: 8.0, master: "PLAIN_BACKUP", ...extrasFor(need(k).title) });
});

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f, "| quiet figures:", QUIET || "full run",
  "| main:", MAIN.join(","), "| backup:", BACK.join(",")));
