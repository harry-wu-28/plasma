// Builds twostream/results/talk/twostream_talk.pptx from twostream/results/talk/figures/*.png and the text in twostream/results/talk/content.md
// ("visualize the theory" framing, quiet-start figures: main slides 1-10, backup B1-B8).
// Run from twostream/results/talk/:  node build_deck.js   (needs pptxgenjs; set NODE_PATH if it is installed elsewhere)
// Re-run after any figure in twostream/results/talk/figures/ changes; images are re-read on every build.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const FIG = (f) => path.join(HERE, "figures", f);
const OUT = path.join(HERE, "twostream_talk.pptx");

// ---- palette (beam colors match the figures) ------------------------------
const K = {
  dark: "171A21",      // title / conclusion background
  card: "262B36",      // card on dark background
  ink: "1A1A1A",       // body text on white
  muted: "596070",     // secondary text on white
  panel: "EEF1F5",     // light card fill
  line: "C9CED6",
  blue: "2166AC",      // beam 1 (moving right) / simulation
  red: "D6604D",       // beam 2 (moving left)
  white: "FFFFFF",
  onDark: "E7EAF0",
  onDarkMuted: "A9B0BD",
};
const FONT = "Arial";

// PNG width/height from the IHDR chunk, so figures keep their aspect ratio.
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
// Largest box of the file's aspect that fits in box (x,y,w,h), centered.
function fitBox(file, box) {
  const { w: pw, h: ph } = pngSize(file);
  const r = pw / ph;
  let w = box.w, h = w / r;
  if (h > box.h) { h = box.h; w = h * r; }
  return { x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h };
}
function fitImage(slide, file, box, extra = {}) {
  slide.addImage({ path: file, ...fitBox(file, box), ...extra });
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "Watching an Instability Grow";
pres.author = "Harry Wu";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

const W = 13.333, H = 7.5, MX = 0.6;
const slideNumber = (color) => ({ x: W - 1.1, y: H - 0.45, w: 0.6, h: 0.3, fontFace: FONT,
  fontSize: 12, color, align: "right" });

// ---- layouts ---------------------------------------------------------------
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: K.dark },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 1.5, w: 7.6, h: 2.5,
        fontFace: FONT, fontSize: 48, bold: true, color: K.white, valign: "bottom", margin: 0 },
      text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: MX, y: 4.2, w: 7.6, h: 1.2,
        fontFace: FONT, fontSize: 24, color: K.onDark, valign: "top", margin: 0 }, text: "" } },
  ],
});
const titleOpts = (color, size = 36) => ({ name: "title", type: "title", x: MX, y: 0.35,
  w: W - 2 * MX, h: 0.8, fontFace: FONT, fontSize: size, bold: true, color, valign: "middle",
  margin: 0 });
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: K.white },
  objects: [{ placeholder: { options: titleOpts(K.ink), text: "" } }],
  slideNumber: slideNumber(K.muted),
});
pres.defineSlideMaster({
  title: "CONTENT_DARK",
  background: { color: K.dark },
  objects: [{ placeholder: { options: titleOpts(K.white), text: "" } }],
  slideNumber: slideNumber(K.onDarkMuted),
});
pres.defineSlideMaster({
  title: "BACKUP",
  background: { color: K.white },
  objects: [
    { placeholder: { options: titleOpts(K.ink, 32), text: "" } },
    { text: { text: "BACKUP", options: { x: MX, y: H - 0.5, w: 2, h: 0.3, fontFace: FONT,
        fontSize: 12, bold: true, color: K.muted, charSpacing: 2, margin: 0 } } },
  ],
  slideNumber: slideNumber(K.muted),
});

// ---- small drawing helpers ---------------------------------------------------
// Rich text: "_x" or "_{...}" makes a subscript, "^{...}" a superscript.
// (Arial lacks Unicode subscript/superscript digits, so use real sub/superscript runs.)
function rich(str, opts = {}) {
  const out = []; let buf = "";
  const push = (t, extra = {}) => { if (t) out.push({ text: t, options: { ...opts, ...extra } }); };
  for (let i = 0; i < str.length; i++) {
    const c = str[i];
    if ((c === "_" || c === "^") && str[i + 1] === "{") {
      const j = str.indexOf("}", i); push(buf); buf = "";
      push(str.slice(i + 2, j), c === "_" ? { subscript: true } : { superscript: true }); i = j;
    } else if (c === "_" && i + 1 < str.length) { push(buf); buf = ""; push(str[++i], { subscript: true }); }
    else buf += c;
  }
  push(buf);
  if (opts.breakLine && out.length) {   // only the last run of a line breaks
    out.forEach((r, k) => { if (k < out.length - 1) delete r.options.breakLine; });
  }
  return out;
}
// Bulleted list of rich strings.
function bullets(items, opts = {}) {
  const runs = [];
  items.forEach((t, j) => {
    const r = rich(t, { ...opts });
    r[0].options.bullet = true;
    if (j < items.length - 1) r[r.length - 1].options.breakLine = true;
    runs.push(...r);
  });
  return runs;
}
// One-line subtitle / plain-English gloss under the title.
function subtitle(slide, text, color = K.muted) {
  slide.addText(rich(text), { x: MX, y: 1.15, w: W - 2 * MX, h: 0.5, fontFace: FONT,
    fontSize: 22, color, margin: 0, valign: "middle", isTextBox: true, objectName: "Subtitle" });
}
// A row of dots ("beam") with a direction arrow and a label to the right of the row.
function beamRow(slide, x, y, w, color, dir, label) {
  const n = 9, d = 0.24, gap = (w - n * d) / (n - 1);
  for (let i = 0; i < n; i++) {
    slide.addShape(pres.shapes.OVAL, { x: x + i * (d + gap), y, w: d, h: d,
      fill: { color }, line: { color, width: 0 }, objectName: `Beam dot ${i}` });
  }
  const ay = y + d / 2;
  const ax0 = dir > 0 ? x + w + 0.25 : x - 0.25;
  const ax1 = dir > 0 ? ax0 + 1.0 : ax0 - 1.0;
  slide.addShape(pres.shapes.LINE, { x: Math.min(ax0, ax1), y: ay, w: 1.0, h: 0,
    line: { color, width: 4, endArrowType: dir > 0 ? "triangle" : undefined,
            beginArrowType: dir < 0 ? "triangle" : undefined }, objectName: "Beam arrow" });
  slide.addText(rich(label), { x: x + w + 1.35, y: ay - 0.25, w: 0.95, h: 0.5,
    fontFace: FONT, fontSize: 24, bold: true, color, align: "left",
    margin: 0, valign: "middle", isTextBox: true, objectName: "Beam label" });
}
function card(slide, x, y, w, h, fill, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12,
    fill: { color: fill }, line: { color: fill, width: 0 }, objectName: name });
}
function arrow(slide, x1, y1, x2, y2, color = K.muted, width = 3) {
  const x = Math.min(x1, x2), y = Math.min(y1, y2);
  const w = Math.abs(x2 - x1), h = Math.abs(y2 - y1);
  slide.addShape(pres.shapes.LINE, { x, y, w, h, flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width, endArrowType: "triangle" }, objectName: "Arrow" });
}
// Number badge (circle with a digit).
function badge(slide, x, y, d, n, fill, color) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill },
    line: { color: fill, width: 0 }, objectName: `Badge ${n}` });
  slide.addText(String(n), { x, y, w: d, h: d, fontFace: FONT, fontSize: 22, bold: true, color,
    align: "center", valign: "middle", margin: 0, isTextBox: true });
}

// ---- speaker notes: twostream/results/talk/content.md (quiet-start version) -------------------
// Two runs: quiet start (job 11092712, to t ≈ 21/ω_p) gives slides 7-9, B4, B6;
// random start (job 11088180, to t ≈ 70/ω_p) gives slide 6, B2, B3, B5.
const NOTES = {
  1: "Hi, I'm Harry. In class we derived the two-stream instability on paper. It's one thing to get an equation, and another to see what it actually describes. So for this project I used a plasma simulation as a camera. I set up the same two electron beams Chen describes, let the computer follow tens of thousands of particles, and watched what happens. I'll show you three things the theory predicts and the simulation makes visible: the wave grows exponentially, it grows in place without moving, and each wavelength grows at the rate Chen's formula gives. I'm not trying to measure anything to many decimal places. The goal is to watch the physics we learned actually happen. First, a quick reminder of what the theory says.",
  2: "Picture two streams of electrons going opposite ways, with a fixed positive background so the plasma is neutral. Suppose there's a tiny ripple, with slightly more electrons in one place. That ripple makes an electric field, which speeds up some electrons and slows others, so they bunch up even more. More bunching means a stronger field, which means more bunching. That feedback loop makes the ripple grow exponentially, like e to the gamma t. Chen's cold-fluid theory predicts a growth rate for every wavelength, with the fastest wave growing at about 0.35 times the plasma frequency. It also predicts that the growing wave has no real frequency. So the wave doesn't travel left or right. It just gets stronger where it is. That makes sense: the two beams are mirror images, so there's no preferred direction to move.",
  3: "So how does the simulation work? A real plasma has far too many electrons to follow one at a time. A particle-in-cell code uses macroparticles instead. Each macroparticle stands for a huge number of real electrons. It carries their combined charge and mass, so its charge-to-mass ratio is the same as one electron's, and it moves exactly the way a single electron would. The particles can be anywhere, but the electric field is stored only at evenly spaced points on a grid. Those are the \"cells\" in particle-in-cell. Storing the field on a grid is what makes this affordable: each particle only talks to the few grid points next to it. The trick is passing information back and forth between the particles and the grid.",
  4: "Every time step, the code goes around this loop. First, deposit: each particle's motion is turned into electric current on the nearby grid points. Second, field solve: the code uses that current to update the electric field on the grid. Third, interpolate: it reads the field back at each particle's position, so every particle knows what force it feels. Fourth, push: Newton's law gives each particle a new velocity and position. Then it starts over. Each step is a tiny slice of time, so the quiet-start run went around this loop about 75,000 times, which took about 13 minutes on 32 CPU cores. Nothing about the two-stream instability is built into these rules. If the instability shows up, it comes from the particles and fields alone.",
  5: "Here's what I simulated. Everything moves along one line, and the box wraps around at the edges. Two electron beams move at a tenth of the speed of light in opposite directions, and the positive background is held fixed, standing in for ions. The beams are nearly cold, close to Chen's cold-beam assumption. I never put a wave in. The instability has to grow from whatever small unevenness the particles start with. I used two runs that differ only in where the particles start. In the random start they're placed at random, so some cells get a few more particles than others, and that makes lumps at every wavelength. In the quiet start they're evenly spaced, with each electron sitting on its positive partner, so the starting charge is almost perfectly smooth. That makes the starting noise about 28 times smaller.",
  6: "This is the simulation itself, from the random-start run, which runs long enough to show the whole story. Horizontal is position, vertical is velocity, and every dot is a macroparticle. Blue is the beam going right, red is the beam going left. At the start you see two flat bands at plus and minus 0.1c. At first nothing seems to happen, because the ripple is buried in the noise. Then ripples appear and get bigger fast. That's the exponential growth: electrons are being sped up and slowed down by the growing wave. Notice that the ripples stay where they are. Finally the beams overlap and curl into vortices. Those are electrons trapped in the wave, and that's where the growth stops. The next three slides use the quiet-start run to measure what you just saw.",
  7: "To see the growth, I break the electric field into its separate waves with a Fourier transform, and follow how strong one wave is over time. This is the wave closest to the fastest-growing one, from the quiet start. The vertical axis is logarithmic, so exponential growth shows up as a straight line. The dashed line is Chen's prediction. I didn't fit it; I just started it at the same point and gave it the theoretical slope. After the first few plasma periods, while the field settles, the simulation sits right on that line for about four e-folds, which is a factor of about 66. And it's still growing when the run ends. The wave hasn't yet become strong enough to trap the electrons, so everything here is the clean, linear growth the theory describes.",
  8: "This picture tests the second prediction. Position is across, time goes up, and color is the electric field: red points one way, blue the other. For the first ten or so units of time it's almost blank, because the quiet start begins with so little noise. Then red and blue stripes appear and get darker as they grow. Now look at the direction of the stripes. They go straight up. A stripe that stays at the same position as time goes on is a wave that isn't moving. If the wave traveled, the stripes would tilt to one side. This is what Re ω equals zero means: the wave grows where it is. Measuring it directly, the real part of the frequency is at most 0.014 times ω_p, which is essentially zero.",
  9: "This is my favorite result. I measured the growth rate of every wave that fits in the box and put them on top of Chen's curve. The black curve is the theory, and each blue dot is one wave from the quiet-start simulation. The dots trace out the shape of the curve: they rise, peak near 0.6, and fall again. The fastest wave grows at 0.342 times ω_p, against 0.354 from theory. Averaged over the six waves in the middle, simulation divided by theory is 0.99, plus or minus 0.06. The grey points are the slow growers: the longest waves on the left, and the shortest ones near the cutoff on the right. Theory says they grow slowly, so by the end of the run they have barely risen above the noise, and the strong waves nearby push them around. That makes them hard to measure, and that's expected, not a failure.",
  10: "To wrap up: I used a particle-in-cell simulation as a camera on the two-stream instability. It shows a wave growing exponentially at the rate Chen predicts. It shows the wave growing in place without traveling, which is what a purely imaginary frequency means. And when I measure every wavelength, the growth rates trace out Chen's curve. One thing I learned about simulations along the way is that where you place the particles at the start really matters. With random positions the noise was so loud that every measurement scattered by tens of percent. Spacing them evenly cut the noise about 28 times and made the theory curve stand out clearly. The one place it's still hard is the slow-growing waves, which barely rise above the noise in the time I ran. And the random-start run, which ran longer, showed what comes after the growth: the electrons get trapped in the wave and the beams mix. Thank you, and I'm happy to take questions.",
};
const VIDEO_NOTE = "[MOVIE (random-start run): click the picture to play (11 s). The still shows three snapshots; the movie is one panel covering the whole run, t = 0 to 70/ω_p, with the time in the top corner. Ripples by about t = 10; around t = 12 the electrons get trapped and roll up into vortices. After t = 20 the movie fast-forwards 3x (not labelled on screen, so say it). If it doesn't play, talk over the still frame, which shows the same stages.]";
// Likely Q&A from content.md, attached to the backup slide each one belongs with.
const QA = {
  1: "Q: Where does the noise come from, and how did the quiet start reduce it? With random positions, the number of particles in a cell fluctuates by about √N, a relative noise of about 1/√N, and that seeds every wavelength. Evenly spacing the particles, with each electron on its positive partner, makes the starting charge nearly zero. The velocities are still random, so some noise comes back, but the effective seed is about 28 times lower.",
  2: "Q: Isn't the quiet start cheating? No. The physics (beams, speeds, temperature, grid, number of particles) is identical. It only removes counting noise that is much larger than in a real plasma, because a real plasma has vastly more particles per cell. The instability still has to grow on its own, and it is not told which wavelength to pick.",
  3: "Q: How did you measure the growth rate, and where do the error bars come from? For each wave, I fit straight lines to the log of its amplitude over many short windows sliding across t ≈ 8–20/ω_p, and take the median. The error bar is the spread between windows, so it shows how much the answer depends on which stretch of time I pick.",
  4: "Q: Why does the wave stay in place (Re ω = 0)? The two beams are identical except for direction, so there's no preferred direction for the wave to move. Mathematically the growing root is purely imaginary. In the quiet-start run the measured real frequency is at most 0.014 ω_p.",
  5: "Q: Why are the grey points (slow growers) so uncertain? Theory says the longest waves (m=1–3) and the waves near the cutoff (m=10–11) grow slowly. By the end of the run they have barely risen above the noise, and the strongly growing waves near the peak also push them around. So their fits are noisy, even with the quiet start.",
  6: "Q: Why does the quiet-start run end before the wave saturates? It was a short test run, to t ≈ 21/ω_p. With less noise the wave starts smaller and needs longer to saturate, about 22–25/ω_p. Everything on slides 7–9 is in the clean linear stage, which is what the theory describes. The random-start run shows what happens after.",
  7: "Q: How did you choose the time step? Entity solves the full Maxwell equations, so light must not cross more than one cell per step. I used half a cell per step (CFL = 0.5), which makes ω_pΔt ≈ 3×10⁻⁴, far below the stability limit of 2 for the particle push.",
  8: "Q: What particle shape did you use? Cloud-in-cell, which is first order: each particle's charge is split between the two nearest grid points according to distance. Smoother shapes reduce noise but cost more. I didn't vary it.",
  9: "Q: What changes with ions (the Buneman instability)? See this slide: the growth is slower, scaling as (m/M)^(1/3), and the wave drifts slowly (Re ω ≈ 0.036 ω_pe) instead of standing still.",
};
const withQA = (notes, ...keys) => [notes, ...keys.map((k) => QA[k])].join("\n\n");

// =============================================================================
// MAIN DECK
pres.addSection({ title: "Talk" });

// 1. Title
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Talk" });
  s.addText([{ text: "Watching an", options: { breakLine: true } }, { text: "Instability Grow" }], { placeholder: "title" });
  s.addText("The two-stream instability in a particle-in-cell simulation", { placeholder: "body" });
  s.addText("Harry Wu  ·  [course name]  ·  [date]", { x: MX, y: 6.0, w: 7.6, h: 0.45,
    fontFace: FONT, fontSize: 20, color: K.onDarkMuted, margin: 0, isTextBox: true,
    objectName: "Author line" });
  s.addText("Simulated with the Entity particle-in-cell (PIC) code", { x: MX, y: 6.45, w: 7.6,
    h: 0.45, fontFace: FONT, fontSize: 18, color: K.onDarkMuted, margin: 0, isTextBox: true });
  card(s, 8.75, 0.9, 4.0, 5.7, K.white, "Art card");
  fitImage(s, path.join(HERE, "assets", "title_vortices.png"), { x: 8.95, y: 1.1, w: 3.6, h: 5.3 },
    { altText: "Simulated electrons curling into vortices in phase space" });
  s.addNotes(NOTES[1]);
}

// 2. Two beams, and what Chen predicts
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("Two beams, and what Chen predicts", { placeholder: "title" });
  subtitle(s, "Instability = a tiny disturbance that grows on its own");
  beamRow(s, 1.75, 2.15, 2.8, K.blue, +1, "+v_0");
  beamRow(s, 1.75, 2.95, 2.8, K.red, -1, "−v_0");
  s.addText("Two beams pass through each other", { x: MX, y: 3.55, w: 6.4, h: 0.5,
    fontFace: FONT, fontSize: 22, color: K.ink, margin: 0, align: "center", valign: "middle",
    isTextBox: true });
  // feedback loop (right)
  const bw = 2.45, bh = 0.85;
  const boxes = [
    { t: "density ripple", x: 8.85, y: 1.8 },
    { t: "electric field", x: 10.25, y: 3.3 },
    { t: "more bunching", x: 7.45, y: 3.3 },
  ];
  boxes.forEach((b, i) => {
    card(s, b.x, b.y, bw, bh, K.panel, `Loop box ${i + 1}`);
    s.addText(b.t, { x: b.x, y: b.y, w: bw, h: bh, fontFace: FONT, fontSize: 20, bold: true,
      color: K.ink, align: "center", valign: "middle", margin: 0.05, isTextBox: true });
  });
  arrow(s, 10.75, 2.75, 11.2, 3.2);    // ripple -> field
  arrow(s, 10.15, 3.72, 9.98, 3.72);   // field -> bunching
  arrow(s, 8.45, 3.2, 8.95, 2.75);     // bunching -> ripple
  s.addText("feedback", { x: 9.15, y: 2.8, w: 1.85, h: 0.4, fontFace: FONT, fontSize: 18,
    italic: true, color: K.muted, align: "center", margin: 0, isTextBox: true });
  // Chen's two predictions
  const cw = (W - 2 * MX - 0.3) / 2, cy = 4.55, ch = 2.3;
  const preds = [
    { h: "Grows exponentially", b: ["like e^{γt}", "fastest: γ ≈ 0.354 ω_p at kv_0 ≈ 0.61 ω_p"] },
    { h: "Grows in place", b: ["Re ω = 0", "the wave doesn't travel left or right"] },
  ];
  preds.forEach((p, i) => {
    const x = MX + i * (cw + 0.3);
    card(s, x, cy, cw, ch, K.dark, `Prediction ${i + 1}`);
    badge(s, x + 0.3, cy + 0.3, 0.6, i + 1, K.white, K.dark);
    s.addText(p.h, { x: x + 1.1, y: cy + 0.3, w: cw - 1.4, h: 0.6, fontFace: FONT, fontSize: 24,
      bold: true, color: K.white, margin: 0, valign: "middle", isTextBox: true });
    s.addText(p.b.flatMap((l, k) => rich(l, { breakLine: k < p.b.length - 1 })), { x: x + 0.3, y: cy + 1.05, w: cw - 0.6, h: 1.05, fontFace: FONT,
      fontSize: 20, color: K.onDark, margin: 0, valign: "top", isTextBox: true });
  });
  s.addNotes(NOTES[2]);
}

// 3. How PIC works: particles and a grid
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("How PIC works: particles and a grid", { placeholder: "title" });
  subtitle(s, "Too many real electrons to follow one by one");
  // diagram (left): grid points on a line, macroparticles scattered between them
  const x0 = 0.9, dx = 0.9, ny = 4.75, nd = 0.22;
  s.addShape(pres.shapes.LINE, { x: x0, y: ny, w: 8 * dx, h: 0, line: { color: K.muted, width: 2 },
    objectName: "Grid line" });
  for (let i = 0; i <= 8; i++) {
    s.addShape(pres.shapes.RECTANGLE, { x: x0 + i * dx - nd / 2, y: ny - nd / 2, w: nd, h: nd,
      fill: { color: K.ink }, line: { color: K.ink, width: 0 }, objectName: `Grid point ${i}` });
  }
  s.addText("grid points: the field E is stored only here", { x: x0 - 0.3, y: ny + 0.3,
    w: 8 * dx + 0.6, h: 0.45, fontFace: FONT, fontSize: 20, color: K.ink, align: "center",
    margin: 0, isTextBox: true });
  // fixed pseudo-random particle positions (x in grid units, y offset), blue and red beams
  const parts = [[0.3, 0.55, 1], [0.8, 1.1, 0], [1.35, 0.7, 1], [1.9, 1.35, 0], [2.6, 0.5, 0],
    [3.2, 1.2, 1], [4.55, 0.95, 0], [5.1, 0.45, 1], [5.7, 1.3, 1], [6.25, 0.75, 0],
    [6.9, 1.15, 1], [7.6, 0.6, 0]];
  const pd = 0.26;
  parts.forEach(([gx, oy, b], i) => {
    const c = b ? K.blue : K.red;
    s.addShape(pres.shapes.OVAL, { x: x0 + gx * dx - pd / 2, y: ny - 0.4 - oy - pd / 2, w: pd, h: pd,
      fill: { color: c }, line: { color: c, width: 0 }, objectName: `Particle ${i}` });
  });
  // highlighted particle talking to its two nearest grid points
  const hx = x0 + 3.9 * dx, hy = ny - 1.55, hd = 0.42;
  s.addShape(pres.shapes.LINE, { x: x0 + 3 * dx, y: hy + hd / 2, w: hx - (x0 + 3 * dx), h: ny - hy - hd / 2,
    flipH: true, line: { color: K.blue, width: 2, dashType: "dash" }, objectName: "Link left" });
  s.addShape(pres.shapes.LINE, { x: hx, y: hy + hd / 2, w: x0 + 4 * dx - hx, h: ny - hy - hd / 2,
    line: { color: K.blue, width: 2, dashType: "dash" }, objectName: "Link right" });
  s.addShape(pres.shapes.OVAL, { x: hx - hd / 2, y: hy - hd / 2, w: hd, h: hd,
    fill: { color: K.blue }, line: { color: K.white, width: 2 }, objectName: "Highlighted particle" });
  s.addText("each particle talks only to its nearest grid points", { x: x0 - 0.3, y: 1.85,
    w: 8 * dx + 0.6, h: 0.45, fontFace: FONT, fontSize: 20, italic: true, color: K.blue,
    align: "center", margin: 0, isTextBox: true });
  // right: macroparticle + grid cards
  const rx = 9.15, rw = 3.6;
  card(s, rx, 1.9, rw, 2.6, K.dark, "Macroparticle card");
  s.addShape(pres.shapes.OVAL, { x: rx + 0.3, y: 2.15, w: 0.55, h: 0.55, fill: { color: K.blue },
    line: { color: K.blue, width: 0 }, objectName: "Macroparticle icon" });
  s.addText("Macroparticle", { x: rx + 1.05, y: 2.1, w: rw - 1.15, h: 0.65, fontFace: FONT,
    fontSize: 22, bold: true, color: K.white, valign: "middle", margin: 0, isTextBox: true });
  s.addText("stands for many electrons, with the same charge-to-mass ratio",
    { x: rx + 0.3, y: 2.85, w: rw - 0.6, h: 1.45, fontFace: FONT, fontSize: 20, color: K.onDark,
      valign: "top", margin: 0, isTextBox: true });
  card(s, rx, 4.75, rw, 2.1, K.panel, "Grid card");
  s.addShape(pres.shapes.RECTANGLE, { x: rx + 0.42, y: 5.05, w: 0.3, h: 0.3, fill: { color: K.ink },
    line: { color: K.ink, width: 0 }, objectName: "Grid icon" });
  s.addText("Grid", { x: rx + 1.05, y: 4.88, w: rw - 1.15, h: 0.65, fontFace: FONT, fontSize: 22,
    bold: true, color: K.ink, valign: "middle", margin: 0, isTextBox: true });
  s.addText("fields live on grid points; particles move freely between them",
    { x: rx + 0.3, y: 5.6, w: rw - 0.6, h: 1.15, fontFace: FONT, fontSize: 20, color: K.ink,
      valign: "top", margin: 0, isTextBox: true });
  s.addNotes(NOTES[3]);
}

// 4. How PIC works: the loop
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("How PIC works: the loop", { placeholder: "title" });
  subtitle(s, "One time step. Nothing about the instability is built into these rules");
  const cx = W / 2, cy = 4.4, bw = 3.4, bh = 1.15, off = 1.55;
  const steps = [
    { n: "1", t: "Deposit", d: "particle motion → grid current", x: cx - bw / 2, y: 1.85 },
    { n: "2", t: "Field solve", d: "current → new electric field", x: cx + off, y: cy - bh / 2 },
    { n: "3", t: "Interpolate", d: "grid field → force on particles", x: cx - bw / 2, y: 6.95 - bh },
    { n: "4", t: "Push", d: "Newton's law moves particles", x: cx - off - bw, y: cy - bh / 2 },
  ];
  steps.forEach((b) => {
    card(s, b.x, b.y, bw, bh, K.panel, `Step ${b.n}`);
    s.addText([
      { text: `${b.n}  ${b.t}`, options: { fontSize: 24, bold: true, color: K.ink, breakLine: true } },
      { text: b.d, options: { fontSize: 18, color: K.muted } },
    ], { x: b.x, y: b.y, w: bw, h: bh, fontFace: FONT, align: "center", valign: "middle",
      margin: 0.05, isTextBox: true });
  });
  const ox = off + bw / 2;
  arrow(s, cx + bw / 2 + 0.1, 2.45, cx + ox, cy - bh / 2 - 0.1);          // 1 -> 2
  arrow(s, cx + ox, cy + bh / 2 + 0.1, cx + bw / 2 + 0.1, 6.35);          // 2 -> 3
  arrow(s, cx - bw / 2 - 0.1, 6.35, cx - ox, cy + bh / 2 + 0.1);          // 3 -> 4
  arrow(s, cx - ox, cy - bh / 2 - 0.1, cx - bw / 2 - 0.1, 2.45);          // 4 -> 1
  s.addText([
    { text: "repeat every", options: { fontSize: 22, color: K.muted, breakLine: true } },
    { text: "time step", options: { fontSize: 28, bold: true, color: K.ink } },
  ], { x: cx - 1.4, y: cy - 0.6, w: 2.8, h: 1.2, fontFace: FONT, align: "center",
    valign: "middle", margin: 0, isTextBox: true });
  s.addNotes(NOTES[4]);
}

// 5. Setup table, plus the two runs
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("The simulation setup", { placeholder: "title" });
  const hdr = { bold: true, color: K.ink, fill: { color: K.panel } };
  const rows = [
    ["Beams", "2 electron beams at ±0.1c, nearly cold (thermal spread 0.01c)"],
    ["Box", "1D, periodic (exit right → enter left), ~7 wavelengths long"],
    ["Grid", "12,288 cells (Debye length ≈ 17 cells)"],
    ["Particles", "4 per cell per beam (~49,000 per beam)"],
    ["Numerics", "Boris push · cloud-in-cell shape · zigzag current deposit"],
  ].map(([a, b]) => [{ text: a, options: hdr }, { text: b, options: { color: K.ink } }]);
  s.addTable(rows, { x: MX, y: 1.35, w: W - 2 * MX, colW: [2.4, W - 2 * MX - 2.4],
    fontFace: FONT, fontSize: 22, rowH: 0.66, valign: "middle", margin: [0, 0.2, 0, 0.2],
    border: { type: "solid", color: K.line, pt: 1 }, objectName: "Setup table" });
  s.addText("No wave added by hand: it grows from tiny unevenness in the particles",
    { x: MX, y: 4.8, w: W - 2 * MX, h: 0.5, fontFace: FONT, fontSize: 22, bold: true,
      color: K.ink, margin: 0, valign: "middle", isTextBox: true });
  const cw = (W - 2 * MX - 0.3) / 2, cy = 5.5, ch = 1.35;
  const runs = [
    { h: "Quiet start", b: "evenly spaced particles → slides 7–9", fill: K.blue },
    { h: "Random start", b: "random positions → the movie", fill: K.dark },
  ];
  runs.forEach((r, i) => {
    const x = MX + i * (cw + 0.3);
    card(s, x, cy, cw, ch, r.fill, `${r.h} card`);
    s.addText([
      { text: r.h, options: { fontSize: 24, bold: true, color: K.white, breakLine: true } },
      { text: r.b, options: { fontSize: 20, color: K.onDark } },
    ], { x: x + 0.3, y: cy, w: cw - 0.6, h: ch, fontFace: FONT, margin: 0, valign: "middle",
      isTextBox: true });
  });
  s.addNotes(NOTES[5]);
}

// 6. What the electrons do (video from the random-start run, still as poster frame)
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("What the electrons do", { placeholder: "title" });
  subtitle(s, "Phase space: each dot is one macroparticle's position and velocity (random-start run)");
  const box = { x: MX, y: 1.75, w: W - 2 * MX, h: 5.25 };
  const vid = FIG("phase_space.mp4"), still = FIG("phase_space.png");
  if (fs.existsSync(vid)) {
    // If playback fails, the poster frame (the three snapshots) stays on screen.
    s.addMedia({ type: "video", path: vid, ...fitBox(still, box),
      cover: "data:image/png;base64," + fs.readFileSync(still).toString("base64"),
      objectName: "Phase space video" });
  } else {
    fitImage(s, still, box, { altText: "Phase space at three times: flat beams, ripples, vortices" });
  }
  s.addNotes(NOTES[6] + (fs.existsSync(vid) ? "\n\n" + VIDEO_NOTE : ""));
}

// 7. The wave grows exponentially (quiet start)
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("The wave grows exponentially", { placeholder: "title" });
  subtitle(s, "Dashed = Chen's rate, not fitted. ~4 e-folds (×66), still growing at the end");
  fitImage(s, FIG("growth_fastest_mode.png"), { x: MX, y: 1.75, w: W - 2 * MX, h: 5.25 },
    { altText: "Amplitude of the fastest wave vs time (quiet start), on Chen's unfitted growth line" });
  s.addNotes(NOTES[7]);
}

// 8. The wave grows in place (quiet start)
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("The wave grows in place", { placeholder: "title" });
  subtitle(s, "Color = electric field. Almost blank at first, then vertical stripes: Re ω ≈ 0");
  fitImage(s, FIG("spacetime_Ex.png"), { x: MX, y: 1.75, w: W - 2 * MX, h: 5.25 },
    { altText: "Electric field versus position and time (quiet start): vertical stripes grow" });
  s.addNotes(NOTES[8]);
}

// 9. SHOWCASE: the simulation traces out Chen's growth-rate curve (quiet start)
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Talk" });
  s.addText("Tracing out Chen's growth-rate curve", { placeholder: "title" });
  subtitle(s, "Black: Chen. Blue: one measured wave each. Pale: slow growers, hard to measure");
  fitImage(s, FIG("growth_rate_vs_k.png"), { x: 0.35, y: 1.7, w: 9.75, h: 5.4 },
    { altText: "Measured growth rate of every box wave (quiet start) on Chen's growth-rate curve" });
  const cx = 10.2, cw = 2.6;
  card(s, cx, 1.95, cw, 4.85, K.panel, "Summary card");
  s.addText([
    { text: "Fastest wave", options: { fontSize: 20, bold: true, color: K.ink, breakLine: true } },
    { text: "0.342 ± 0.024", options: { fontSize: 24, bold: true, color: K.blue, breakLine: true } },
    { text: "theory 0.354", options: { fontSize: 20, color: K.ink, breakLine: true } },
    { text: " ", options: { fontSize: 14, breakLine: true } },
    { text: "Waves 4–9", options: { fontSize: 20, bold: true, color: K.ink, breakLine: true } },
    { text: "sim ÷ theory", options: { fontSize: 18, color: K.muted, breakLine: true } },
    { text: "0.99 ± 0.06", options: { fontSize: 24, bold: true, color: K.blue, breakLine: true } },
    ...rich("γ in units of ω_p", { fontSize: 16, color: K.muted }),
  ], { x: cx + 0.1, y: 1.95, w: cw - 0.2, h: 4.85, fontFace: FONT, align: "center",
    valign: "middle", margin: 0, isTextBox: true });
  s.addNotes(NOTES[9]);
}

// 10. What we saw
{
  const s = pres.addSlide({ masterName: "CONTENT_DARK", sectionTitle: "Talk" });
  s.addText("What we saw", { placeholder: "title" });
  const n = 3, gap = 0.3, cw = (W - 2 * MX - gap * (n - 1)) / n, cy = 1.45, ch = 3.1;
  const seen = [
    "A wave grew exponentially, along Chen's slope",
    "It grew in place, without traveling (Re ω = 0)",
    "Each wavelength's growth rate traced out Chen's curve",
  ];
  seen.forEach((t, i) => {
    const x = MX + i * (cw + gap);
    card(s, x, cy, cw, ch, K.card, `Seen ${i + 1}`);
    badge(s, x + 0.3, cy + 0.3, 0.6, i + 1, K.white, K.dark);
    s.addText(rich(t), { x: x + 0.3, y: cy + 1.1, w: cw - 0.6, h: ch - 1.3, fontFace: FONT,
      fontSize: 24, bold: true, color: K.white, margin: 0, valign: "top", isTextBox: true });
  });
  card(s, MX, 4.85, W - 2 * MX, 1.05, K.card, "Lesson card");
  s.addText([
    { text: "PIC lesson: ", options: { bold: true, color: "8FC1E8" } },
    { text: "where the particles start matters; a quiet start made the physics clear",
      options: { color: K.onDark } },
  ], { x: MX + 0.3, y: 4.85, w: W - 2 * MX - 0.6, h: 1.05, fontFace: FONT, fontSize: 22,
    margin: 0, valign: "middle", isTextBox: true });
  s.addText("Thank you! Questions?", { x: MX, y: 6.25, w: W - 2 * MX, h: 0.6, fontFace: FONT,
    fontSize: 28, bold: true, color: K.white, margin: 0, valign: "middle", isTextBox: true });
  s.addNotes(NOTES[10]);
}

// =============================================================================
// BACKUP (B1-B8, in content.md order)
pres.addSection({ title: "Backup" });
const backupSlide = (title) => {
  const s = pres.addSlide({ masterName: "BACKUP", sectionTitle: "Backup" });
  s.addText(title, { placeholder: "title" });
  return s;
};
const backupSubtitle = (s, text) => s.addText(rich(text), { x: MX, y: 1.15, w: W - 2 * MX, h: 0.5,
  fontFace: FONT, fontSize: 20, color: K.muted, margin: 0, valign: "middle", isTextBox: true,
  objectName: "Subtitle" });
// Text-only backup: one light card with bullets.
function backupBullets(title, items, notes) {
  const s = backupSlide(title);
  card(s, MX, 1.45, W - 2 * MX, 4.2, K.panel, "Bullet card");
  s.addText(bullets(items), { x: MX + 0.4, y: 1.75, w: W - 2 * MX - 0.8, h: 3.7, fontFace: FONT,
    fontSize: 24, color: K.ink, margin: 0, valign: "top", paraSpaceAfter: 18, isTextBox: true });
  s.addNotes(notes);
}
// Figure-left, bullets-right backup.
function backupFigBullets(title, fig, alt, items, notes) {
  const s = backupSlide(title);
  fitImage(s, fig, { x: MX - 0.1, y: 1.4, w: 7.7, h: 5.5 }, { altText: alt });
  card(s, 8.3, 1.45, W - MX - 8.3, 5.3, K.panel, "Bullet card");
  s.addText(bullets(items), { x: 8.55, y: 1.7, w: W - MX - 8.8, h: 4.8, fontFace: FONT,
    fontSize: 18, color: K.ink, margin: 0, valign: "top", paraSpaceAfter: 12, isTextBox: true });
  s.addNotes(notes);
}

// B1. Chen's graphical method
{
  const s = backupSlide("B1  Chen's graphical method: stable vs unstable");
  s.addText(rich("1 = ½ω_p²[ 1/(ω − kv_0)² + 1/(ω + kv_0)² ]"), { x: MX, y: 1.15, w: 8.6, h: 0.6,
    fontFace: FONT, fontSize: 26, color: K.ink, margin: 0, valign: "middle", isTextBox: true,
    objectName: "Dispersion relation" });
  fitImage(s, FIG("dispersion_stable_unstable.png"), { x: MX - 0.1, y: 1.85, w: 9.0, h: 4.95 },
    { altText: "F(omega) for a stable short wave (4 crossings) and a growing long wave (2 crossings)" });
  const cx = 9.75, cw = 3.0;
  card(s, cx, 2.1, cw, 2.0, K.panel, "Unstable band card");
  s.addText([
    { text: "Grows if", options: { fontSize: 20, color: K.muted, breakLine: true } },
    ...rich("kv_0 < ω_p", { fontSize: 30, bold: true, color: K.ink, breakLine: true }),
    { text: "(long waves)", options: { fontSize: 20, color: K.muted } },
  ], { x: cx + 0.25, y: 2.1, w: cw - 0.5, h: 2.0, fontFace: FONT, valign: "middle", margin: 0,
    isTextBox: true });
  card(s, cx, 4.4, cw, 2.2, K.panel, "Fastest growth card");
  s.addText([
    { text: "Fastest growth", options: { fontSize: 20, color: K.muted, breakLine: true } },
    ...rich("γ = ω_p/(2√2)", { fontSize: 28, bold: true, color: K.ink, breakLine: true }),
    ...rich("at kv_0 ≈ 0.61 ω_p", { fontSize: 20, color: K.muted }),
  ], { x: cx + 0.25, y: 4.4, w: cw - 0.5, h: 2.2, fontFace: FONT, valign: "middle", margin: 0,
    isTextBox: true });
  s.addNotes(withQA("From the cold-fluid equations (continuity, Newton's law, and Gauss's law) you get this dispersion relation, which says which frequencies go with each wavenumber. Chen solves it by plotting the right-hand side and seeing where it crosses one. For a short wave it crosses four times, so all four roots are real and the wave only oscillates. For a longer wave it crosses only twice, so the other two roots must be complex, and a complex frequency means growth. The growing root turns out to be purely imaginary, which is why the wave stays in place.", 4));
}

// B2. Trapped electrons (random start)
{
  const s = backupSlide("B2  Trapped electrons (Chen Fig. 7.12), random-start run");
  backupSubtitle(s, "Black line: trapping boundary from the simulation's own potential. Dots: simulated electrons");
  fitImage(s, FIG("trapping_separatrix.png"), { x: MX, y: 1.75, w: W - 2 * MX, h: 5.2 },
    { altText: "Trapping boundary computed from the measured field, over the simulated electrons" });
  s.addNotes(withQA("This is from the random-start run, which runs past saturation. I took its electric potential at saturation and computed the boundary between electrons trapped in the wave and electrons that pass over it: the black line. The simulated electrons swirl inside the boundary and pile up along its edge, which is Chen's trapped-orbit picture. Trapping is what stops the growth.", 6));
}

// B3. The beams flatten (random start)
{
  const s = backupSlide("B3  The beams flatten (Chen Fig. 7.19), random-start run");
  backupSubtitle(s, "Two narrow peaks at ±0.1c become one broad hump, flat near zero, wings to ±0.25c");
  fitImage(s, FIG("fv_plateau.png"), { x: MX, y: 1.75, w: W - 2 * MX, h: 5.2 },
    { altText: "Velocity distribution: two narrow beam peaks at the start, one broad flat-topped hump at the end" });
  s.addNotes("This counts how many electrons have each velocity, with the same total in every curve. It starts as two narrow peaks, one per beam. By the end the beams have mixed into one broad hump, flat-topped near zero velocity. It isn't a perfectly flat plateau, but the free energy of the two beams is gone, which is the flattening Chen sketches in Figure 7.19.");
}

// B4. Why the starting positions matter (quiet-start points only)
backupFigBullets("B4  Why the starting positions matter: a PIC lesson",
  FIG("gamma_k_quiet_vs_random.png"),
  "Measured growth rate of every box wave (quiet start) with error bars, on Chen's curve",
  [
    "Random positions → cell-to-cell counting noise at every wavelength (~1/√N)",
    "Evenly spaced, each electron on its positive partner → almost no starting charge",
    "Starting noise 28× lower → about 3.3 more clean e-folds",
    "Quiet-start rates follow Chen's curve (m = 4–9: 0.99 ± 0.06, spread 15%)",
  ],
  withQA("The same beams, grid, and number of particles can give a clear picture or a blurry one, depending only on where the particles start. With random positions, some cells get more particles than others by chance, which seeds every wavelength with a fairly large ripple. In my first run that left only about three e-folds of growth, and single waves scattered by about 30 percent, although the average still came out at 0.99 plus or minus 0.16. With evenly spaced positions, and each electron sitting on its positive partner, the starting charge is nearly zero everywhere. The velocities are still random, so some noise creeps back in, but the effective seed is about 28 times smaller. That buys about 3.3 extra e-folds of clean growth, and the measured growth rates settle onto Chen's curve, as this plot shows. Same physics, much clearer picture.", 1, 2, 5));

// B5. Before: the random-start numbers
backupFigBullets("B5  Before: the random-start numbers",
  FIG("random_start/growth_rate_vs_k.png"),
  "Growth rate vs wavenumber from the random-start run: scattered points with large error bars",
  [
    "Random start: only ~3 e-folds of growth before saturation",
    "Fastest wave (m = 7): 0.36 ± 0.12 ω_p vs theory 0.354 ω_p",
    "Waves m = 4–9: sim ÷ theory = 0.99 ± 0.16; single waves scatter ~±30%",
    "Sliding the fit window within t = 40–160 (code units) shifts γ by 0.06–0.19 ω_p",
  ],
  withQA("This is where I started. With random starting positions the noise floor was high, so the fastest wave grew only about three e-folds before trapping stopped it. Over such a short stretch the fitted growth rate depended on exactly which times I chose, by up to about 0.19 ω_p. On average it still agreed with theory, 0.99 plus or minus 0.16, but any single wave was uncertain by about 30 percent. That's what motivated the quiet start.", 3));

// B6. Space-time with the noise made visible (quiet start)
{
  const s = backupSlide("B6  Space-time with the noise made visible");
  backupSubtitle(s, "Same as slide 8, but each time row is divided by its own rms field");
  fitImage(s, FIG("spacetime_Ex_normalized.png"), { x: MX, y: 1.75, w: W - 2 * MX, h: 5.2 },
    { altText: "Electric field divided by its rms at each time, versus position and time (quiet start)" });
  s.addNotes("On slide 8 the early field is too weak to see. Here I rescale each moment in time by its own typical field strength, so the pattern is visible from the start. You can see the stripes pick out their positions early on and stay there.");
}

// B7, B8: text backups
backupBullets("B7  Numerical choices", [
  "Boris push; cloud-in-cell (first-order) particle shape; zigzag charge-conserving current deposit",
  "Time step: light crosses half a cell per step (CFL = 0.5) → ω_pΔt ≈ 3×10^{-4}",
  "Grid: Debye length ≈ 17 cells, so no grid-heating instability",
  "Random-start run: total energy constant to better than 1 part in 100,000",
], withQA("These are the settings behind both runs. The time step is set by the speed of light, because Entity solves the full Maxwell equations, and it ends up far smaller than the plasma needs. The grid is fine enough to avoid the artificial heating that coarse grids cause.", 7, 8));

backupBullets("B8  With ions instead: the Buneman instability", [
  "Electron beam through ions at rest: the heavy ions respond slowly",
  "Growth scales as (m/M)^{1/3}: γ_{max} ≈ 0.054 ω_{pe} at kv_0 ≈ ω_{pe} for hydrogen",
  "That wave does travel slowly: Re ω ≈ 0.036 ω_{pe}",
  "Needs a fixed \"return current\" in the code; run in progress",
], withQA("If one beam is replaced by ions at rest, you get the Buneman instability. Because ions are heavy, it grows six to seven times slower, and unlike our case the growing wave has a real frequency, so it drifts. Simulating it needs an extra fixed current to stop the beam's own current from pulling it back. That run is still in progress.", 9));

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f));
