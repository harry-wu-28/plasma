# Two-stream talk: slide text and speaker notes

**Framing:** we use a PIC simulation to *see* Chen's two-stream theory happen. The wave grows
exponentially out of noise, it grows in place without traveling, and the growth rate of each
wave traces out Chen's curve. The goal is to visualize the physics, not to run a precision test.

Talk (~12 min) + Q&A. Main slides 1–12 (~1,755 words of notes), then backup slides
B1–B8, then likely Q&A. Figures are in `twostream/results/talk/figures/` (random-start versions in
`twostream/results/talk/figures/random_start/`).

**Two runs, same grid:**
- *Quiet start* (job 11093069, `pgens/streaming_quiet`, ppc0 = 64 = 16 per cell per beam,
  245,760 steps to t ≈ 70/ω_p, 1 h 31 min on 1 node × 32 threads): particles start evenly
  spaced. It gives every figure in the main talk and B1–B4, B6: the movie (to 40/ω_p, then 3×
  fast-forward to 70/ω_p), phase-space stills at t = 0, 20, 33/ω_p, growth, space-time and
  γ(k) (cut at saturation, t ≈ 26.8/ω_p), the trapping boundary at 33/ω_p (about 6/ω_p after
  saturation), and f(v) (late average t = 63–70/ω_p).
- *Random start* (baseline, CPU job 11088180, ppc0 = 16 = 4 per cell per beam, to t ≈ 70/ω_p):
  particles start at random positions. Used only for the "before" numbers (B5) and the
  comparison story in B4.
- Seed noise vs the random start: 48× lower overall (+3.9 clean e-folds). Evenly spaced positions
  alone give 28× (measured in smoke job 11092712, both at ppc0 = 16); the 4× extra particles give a
  further 1.8×. The smoke run is not otherwise used.

**Units on every slide (same as Chen and the figures):** ω_p is the plasma frequency of *all*
the electrons (both beams together). Wavenumber is written as kv₀/ω_p, time as t in 1/ω_p.

---

## Slide 1: Watching an Instability Grow: the Two-Stream Instability in a Particle-in-Cell Simulation

**Bullets**
- Harry Wu, [course name], [date]
- Simulated with the Entity particle-in-cell (PIC) code

**Figure:** `twostream/results/talk/assets/title_vortices.png` (background)

**Speaker notes**
Hi, I'm Harry. In class we derived the two-stream instability on paper. It's one thing to get
an equation, and another to see what it actually describes. So for this project I used a
plasma simulation as a camera. I set up the same two electron beams Chen describes, let the
computer follow tens of thousands of particles, and watched what happens. I'll show you three
things the theory predicts and the simulation makes visible: the wave grows exponentially, it
grows in place without moving, and each wavelength grows at the rate Chen's formula gives.
I'm not trying to measure anything to many decimal places. The goal is to watch the physics we
learned actually happen. First, a quick reminder of what the theory says.

---

## Slide 2: Two beams, and what Chen predicts

**Bullets**
- Two electron beams pass through each other at ±v₀
- Ripple → electric field → more bunching → bigger ripple: grows as e^{γt}
- The growing wave has Re ω = 0: it grows in place and doesn't travel
- Fastest growth: γ_max = ω_p/(2√2) ≈ 0.354 ω_p, at kv₀ ≈ 0.61 ω_p

**Figure:** bunching cartoon (two rows of beam particles with arrows, as in the deck)

**Speaker notes**
Picture two streams of electrons going opposite ways, with a fixed positive background so the
plasma is neutral. Suppose there's a tiny ripple, with slightly more electrons in one place.
That ripple makes an electric field, which speeds up some electrons and slows others, so they
bunch up even more. More bunching means a stronger field, which means more bunching. That
feedback loop makes the ripple grow exponentially, like e to the gamma t. Chen's cold-fluid
theory predicts a growth rate for every wavelength, with the fastest wave growing at about
0.35 times the plasma frequency. It also predicts that the growing wave has no real
frequency. So the wave doesn't travel left or right. It just gets stronger where it is. That
makes sense: the two beams are mirror images, so there's no preferred direction to move.

---

## Slide 3: The math: fastest growth rate and its wavelength

**Bullets**
- Dispersion relation, two cold beams at ±v₀ (each with half the electrons):
  1 = ½ω_p²[ 1/(ω − kv₀)² + 1/(ω + kv₀)² ]   →   (ω² − k²v₀²)² = ω_p²(ω² + k²v₀²)
- For kv₀ < ω_p one root has ω² < 0, so ω = iγ: the wave grows, with
  γ² = (ω_p/2)√(ω_p² + 8k²v₀²) − k²v₀² − ω_p²/2
- Fastest growth: set dγ²/d(k²v₀²) = 0, which gives k²v₀² = (3/8) ω_p²:
  kv₀ = √(3/8) ω_p ≈ 0.612 ω_p,   γ_max = ω_p/(2√2) ≈ 0.354 ω_p
- Peak wavelength (v₀ ≈ 0.1c): λ = 2π/k ≈ 10.3 v₀/ω_p ≈ 1.02 c/ω_p
- Periodic box, L ≈ 7.0 c/ω_p: only waves that fit a whole number of times exist, k_m = 2πm/L
  L/λ ≈ 6.9 → nearest is m = 7: kv₀ ≈ 0.624 ω_p, γ ≈ 0.353 ω_p (m = 6: 0.347, m = 8: 0.342)

**Figure:** none (equations)

**Speaker notes**
Here's where the 0.354 comes from. Start from the dispersion relation for two cold beams, each
holding half the electrons. Clearing the fractions gives a quadratic in omega squared. One of
its roots is negative whenever k v0 is less than omega_p, so omega is imaginary, omega equals i
gamma, and the wave grows. That root gives gamma squared as a function of k. To find the fastest
wave, I set the derivative with respect to k squared v0 squared to zero. That gives k v0 equals
the square root of three eighths times omega_p, about 0.61, and plugging back in, gamma max is
omega_p over two root two, about 0.354 omega_p. Turning k into a wavelength: lambda is 2 pi over
k, about 10 v0 over omega_p, which for beams at a tenth of the speed of light is about one c
over omega_p. But my box is periodic, so only waves that fit a whole number of times can exist.
The box is about 7.0 c over omega_p long, so the theory peak would fit about 6.9 times.
(If asked where 7.0 comes from: the box is 100 code units long, and the code's units set c over
omega_p to 10 for a reference density. My electrons are half that density, and omega_p goes as
the square root of density, so c over omega_p stretches by root two to about 14.1 units. A small
relativistic correction for the moving beams makes it about 14.2, and 100 divided by that is
about 7.0.) The
nearest allowed wave is mode 7, seven wavelengths across the box. Its theoretical growth rate is
0.353, almost exactly the maximum, while its neighbours, modes 6 and 8, are a bit slower. That's
why mode 7 is the fastest-growing wave in the simulation.

---

## Slide 4: How PIC works: particles and a grid

**Bullets**
- Too many real electrons to follow one by one
- Macroparticles: each one stands for many electrons, with the same charge-to-mass ratio
- Electric field is stored only at points on a grid
- Particles move freely between grid points

**Figure:** `assets/sourced/warpx_pic_particles_grid.png` (cropped). Credit: WarpX documentation (warpx.readthedocs.io), © 2018 The Regents of the University of California, BSD-3-Clause-LBNL license

**Speaker notes**
So how does the simulation work? A real plasma has far too many electrons to follow one at a
time. A particle-in-cell code uses macroparticles instead. Each macroparticle stands for a huge
number of real electrons. It carries their combined charge and mass, so its charge-to-mass
ratio is the same as one electron's, and it moves exactly the way a single electron would.
The particles can be anywhere, but the electric field is stored only at evenly spaced points
on a grid. Those are the "cells" in particle-in-cell. Storing the field on a grid is what
makes this affordable: each particle only talks to the few grid points next to it. The trick
is passing information back and forth between the particles and the grid.

---

## Slide 5: How PIC works: the loop

**Bullets**
- Deposit: particle motion → current on the grid
- Field solve: current → new electric field
- Interpolate: field on the grid → force on each particle
- Push: Newton's law moves each particle; repeat each time step

**Figure:** `assets/sourced/warpx_pic_cycle.png`. Credit: WarpX documentation (warpx.readthedocs.io), © 2018 The Regents of the University of California, BSD-3-Clause-LBNL license

**Speaker notes**
Every time step, the code goes around this loop. First, deposit: each particle's motion is
turned into electric current on the nearby grid points. Second, field solve: the code uses
that current to update the electric field on the grid. Third, interpolate: it reads the field
back at each particle's position, so every particle knows what force it feels. Fourth, push:
Newton's law gives each particle a new velocity and position. Then it starts over. Each step
is a tiny slice of time, so my main run went around this loop about 250,000 times, which took
an hour and a half on one 32-core node. Nothing about the two-stream instability is built into these
rules. If the instability shows up, it comes from the particles and fields alone.

---

## Slide 6: How PIC works: one time step in detail

**Bullets**
- Deposit: particle motion → current J on the grid (charge-conserving "zigzag" scheme), smoothed over neighboring cells (4 passes)
- Field solve, 1D Ampère's law: E^{n+1} = E^{n} − (Δt/ε₀) J^{n+½}
- Interpolate: field at each particle = distance-weighted average of its 2 nearest grid points ("cloud-in-cell")
- Push (Boris, which is leapfrog in 1D): v^{n+½} = v^{n−½} + (q/m) E^{n} Δt,   x^{n+1} = x^{n} + v^{n+½} Δt
- Time step: light crosses ½ a cell per step (CFL = 0.5) → ω_pΔt ≈ 3×10⁻⁴ (leapfrog only needs ω_pΔt < 2)

**Figure:** none (equations)

**Speaker notes**
Here's what each step actually computes in my run. Deposit: each particle's motion becomes
current on the nearby grid points, using a scheme that conserves charge exactly, so Gauss's law
stays satisfied. The current is then smoothed over neighboring cells to cut noise. Field solve:
in one dimension, Ampère's law just says the electric field changes by minus the current over
epsilon naught, times the time step. Interpolate: the field felt by a particle is a weighted
average of the two nearest grid points, weighted by distance; that's the cloud-in-cell shape.
Push: Entity uses the Boris pusher, which in 1D with no magnetic field is the leapfrog scheme.
Velocities live half a step offset from positions, and get a kick of q over m times E. The time
step is set by the speed of light: light may cross only half a cell per step. That makes
omega_p delta t about 3 times ten to the minus four, far below the leapfrog limit of 2.

---

## Slide 7: The simulation setup

**Bullets**
- 1D box with periodic edges; two equal electron beams at ±0.1c on a fixed positive background
- No wave added by hand: the instability grows from tiny unevenness in the particles
- Everything shown comes from a quiet start (evenly spaced particles); a random start is only for comparison

**Table**

| Setting | Value |
|---|---|
| Beams | 2 electron beams, ±0.1c, equal density; thermal spread 0.01c |
| Box | length ≈ 7 c/ω_p, holds ~7 wavelengths of the fastest wave |
| Grid | 12,288 cells; Debye length ≈ 17 cells |
| Particles | quiet start: 16 per cell per beam (~197,000 per beam); random start: 4 per cell per beam |
| Time step and numerics | ω_pΔt ≈ 3×10⁻⁴; Boris push, cloud-in-cell shape, zigzag current deposit |

**Speaker notes**
Here's what I simulated. Everything moves along one line, and the box wraps around at the
edges. Two electron beams move at a tenth of the speed of light in opposite directions, and
the positive background is held fixed, standing in for ions. The beams are nearly cold, close
to Chen's cold-beam assumption. I never put a wave in. The instability has to grow from
whatever small unevenness the particles start with. Everything I'll show comes from a quiet
start. If you place particles at random, some cells get a few more than others, and that makes
lumps at every wavelength. In the quiet start they're evenly spaced, with each electron sitting
on its positive partner, so the starting charge is almost perfectly smooth. That alone makes the starting noise about 28 times smaller.
My main quiet-start run also uses four times as many particles, which cuts it almost twice more,
so it starts about 48 times quieter than the random start.

---

## Slide 8: What the electrons do

**Bullets**
- Each dot: one macroparticle's position and velocity (phase space)
- Start: two flat beams at ±0.1c
- Ripples appear, grow, and roll up into vortices
- Movie runs at full speed to 40/ω_p, then 3× fast-forward to the end (70/ω_p)

**Figure:** `phase_space.mp4` (poster frame `phase_space.png`; click to play)

**Speaker notes**
This is the simulation itself. Horizontal is position, vertical is velocity, and every dot is
a macroparticle.
Blue is the beam going right, red is the beam going left. At the start you see two flat bands
at plus and minus 0.1c. At first nothing seems to happen, because the ripple is buried in the
noise. Then ripples appear and get bigger fast. That's the exponential growth: electrons are
being sped up and slowed down by the growing wave. Notice that the ripples stay where they
are. Finally the beams overlap and curl into vortices. Those are electrons trapped in the
wave, and that's where the growth stops. The next three slides
measure what you just saw.

---

## Slide 9: The wave grows exponentially

**Bullets**
- Amplitude of the fastest-growing wave, on a log scale (quiet start)
- Dashed line: Chen's growth rate, not fitted, only started at the same point
- Follows the theory slope for about 4.2 e-folds, a factor of ~70 (t ≈ 10 → 22.5/ω_p)
- Then growth stops (saturation) at t ≈ 27/ω_p

**Figure:** `growth_fastest_mode.png`

**Speaker notes**
To see the growth, I break the electric field into its separate waves with a Fourier
transform, and follow how strong one wave is over time. This is the wave closest to the
fastest-growing one, from the quiet start. The vertical axis is logarithmic, so exponential
growth shows up as a straight line. The dashed line is Chen's prediction. I didn't fit it; I
just started it at the same point and gave it the theoretical slope. After the first few
plasma periods, while the field settles, the simulation sits right on that line from about 10
to 22 over ω_p. That's about four e-folds, a factor of about 70. Then the curve bends over and
flattens at about 27 over ω_p. That's saturation: the wave has become strong enough to trap
the electrons, and the simple linear theory no longer applies. The straight stretch is the
clean, linear growth the theory describes.

---

## Slide 10: The wave grows in place

**Bullets**
- Color = electric field (red and blue: opposite directions); position across, time up
- Almost blank at first: the quiet start has very little noise
- Stripes appear and darken, and they are vertical: the wave stays where it is
- Measured real frequency |Re ω| ≤ 0.024 ω_p, essentially zero

**Figure:** `spacetime_Ex.png`

**Speaker notes**
This picture tests the second prediction. Position is across, time goes up, and color is the
electric field: red points one way, blue the other. For the first ten or so units of time it's
almost blank, because the quiet start begins with so little noise. The dashed line at the top
marks saturation. Then red and blue stripes
appear and get darker as they grow. Now look at the direction of the stripes. They go
straight up. A stripe that stays at the same position as time goes on is a wave that isn't
moving. If the wave traveled, the stripes would tilt to one side. This is what Re ω equals
zero means: the wave grows where it is. Measuring it directly, the real part of the frequency
is at most 0.024 times ω_p, which is essentially zero.

---

## Slide 11: The simulation traces out Chen's growth-rate curve

**Bullets**
- Black: Chen's growth rate for each wavelength; blue: one measured wave each
- Fastest wave (m=7): 0.339 ± 0.014 ω_p vs. theory 0.354 ω_p
- Seven waves land on the curve; m=4–9: simulation/theory = 0.96 ± 0.04, typical spread 9%
- Grey: slow growers (the three longest waves and the one nearest the cutoff) stay close to the noise

**Figure:** `growth_rate_vs_k.png`

**Table** (under the figure)

| | Fastest growth rate | Where |
|---|---|---|
| Theory (Chen) | γ_max = ω_p/(2√2) ≈ 0.354 ω_p | kv₀ = √(3/8) ω_p ≈ 0.612 ω_p (k ≈ 6.2 ω_p/c) |
| Simulation | 0.339 ± 0.014 ω_p | kv₀ ≈ 0.624 ω_p (k ≈ 6.3 ω_p/c), box wave m = 7 |

**Speaker notes**
This is my favorite result. I measured the growth rate of every wave that fits in the box and
put them on top of Chen's curve. The black curve is the theory, and each blue dot is one wave
from the quiet-start simulation. Seven waves land on the curve: they rise, peak near 0.6, and
fall again, just like the theory. The fastest wave grows at 0.339 times ω_p, against 0.354
from theory. The table under the plot puts them side by side: the box only allows certain
wavelengths, so the closest one, m equals 7, sits at 0.624 instead of exactly 0.612. Averaged
over the six waves in the middle, simulation divided by theory is 0.96,
plus or minus 0.04, so the simulation runs about 4 percent slow. The grey points are the slow
growers: the three longest waves on the left and the one nearest the cutoff on the right. They
grow so slowly that they barely rise above the noise before the fast waves saturate, so they
are hard to measure. That's expected, not a failure.

---

## Slide 12: What we saw

**Bullets**
- A wave grew exponentially, along Chen's slope, out of a nearly smooth start
- It grew in place, without traveling, as Re ω = 0 predicts
- Each wavelength's growth rate traced out Chen's curve (0.96 ± 0.04)
- PIC lesson: where the particles start matters, and a quiet start made the physics clear

**Figure:** none, or a small repeat of `growth_rate_vs_k.png`

**Speaker notes**
To wrap up: I used a particle-in-cell simulation as a camera on the two-stream instability.
It shows a wave growing exponentially at the rate Chen predicts. It shows the wave growing in
place without traveling, which is what a purely imaginary frequency means. And when I measure
every wavelength, the growth rates trace out Chen's curve. One thing I learned about
simulations along the way is that where you place the particles at the start really matters.
With random positions the noise was so loud that every measurement scattered by tens of
percent. Spacing them evenly cut the noise about 28 times and made the theory curve stand out
clearly. The one place it's still hard is the slow-growing waves, which barely rise above the
noise before the fast waves saturate. And after the growth, the same run shows what Chen
describes next: the electrons get trapped in the wave and the beams mix. Thank you, and I'm happy
to take questions.

---

# Backup slides

## B1: Chen's graphical method (stable vs unstable)

**Bullets**
- Dispersion relation: 1 = ½ω_p² [1/(ω − kv₀)² + 1/(ω + kv₀)²]
- Short waves: the curve crosses 1 four times → 4 real roots → just oscillates
- Long waves (kv₀ < ω_p): only 2 crossings → the other 2 roots are complex → grows
- Exact solution: γ_max = ω_p/(2√2) at kv₀ = √(3/8) ω_p ≈ 0.61 ω_p

**Figure:** `dispersion_stable_unstable.png`

**Speaker notes**
From the cold-fluid equations (continuity, Newton's law, and Gauss's law) you get this
dispersion relation, which says which frequencies go with each wavenumber. Chen solves it by
plotting the right-hand side and seeing where it crosses one. For a short wave it crosses four
times, so all four roots are real and the wave only oscillates. For a longer wave it crosses
only twice, so the other two roots must be complex, and a complex frequency means growth. The
growing root turns out to be purely imaginary, which is why the wave stays in place.

---

## B2: Trapped electrons (Chen Fig. 7.12)

**Bullets**
- Black line: trapping boundary computed from the simulation's own electric potential
- Dots: simulated electrons (blue = right-moving beam, red = left-moving beam)
- Electrons inside the boundary are trapped in the wave's potential wells

**Figure:** `trapping_separatrix.png`

**Speaker notes**
I took the electric potential from the simulation at t ≈ 33 over ω_p, shortly after saturation, when the vortices are fully formed, and computed the boundary between electrons trapped in the wave and electrons that
pass over it: the black line. The simulated electrons swirl inside the boundary and pile up
along its edge, which is Chen's trapped-orbit picture. Trapping is what stops the growth.

---

## B3: The beams flatten (Chen Fig. 7.19)

**Bullets**
- Velocity distribution starts as two narrow peaks at ±0.1c
- By the end (t ≈ 63–70/ω_p): one broad hump near zero, wings out to about ±0.25c
- The beams' ordered motion has become spread, so nothing is left to drive the wave

**Figure:** `fv_plateau.png`

**Speaker notes**
This counts how many electrons have each velocity, with the same total in every curve. It
starts as two narrow peaks, one per beam. By the end of the run the beams have mixed into one
broad hump around zero velocity. It isn't a perfectly flat plateau, but the two separate beams
are gone, and with them the free energy that drove the wave. That's the flattening Chen
sketches in Figure 7.19.

---

## B4: Why the starting positions matter: a PIC lesson

**Bullets**
- Random positions → cell-to-cell counting noise at every wavelength (~1/√N)
- Evenly spaced positions, each electron on its positive partner → almost no starting charge
- Evenly spaced positions cut the seed noise 28×; 4× more particles cut it a further 1.8× (48× overall)
- Result: ~3.9 more clean e-folds, and seven waves on Chen's curve (m=4–9: 0.96 ± 0.04, spread 9%)

**Figure:** `gamma_k_quiet_vs_random.png` (quiet-start points with Chen's curve)

**Speaker notes**
The same beams and grid can give a clear picture or a blurry one, depending on where the
particles start. With random positions, some cells get more
particles than others by chance, which seeds every wavelength with a fairly large ripple. In my
first run that left only about three e-folds of growth, and single waves scattered by about
30 percent, although the average still came out at 0.99 plus or minus 0.16. With evenly spaced
positions, and each electron sitting on its positive partner, the starting charge is nearly
zero everywhere. The velocities are still random, so some noise creeps back in, but the
effective seed is about 28 times smaller. My main quiet run also has four times as many
particles, which cuts the noise almost two times more, about 48 times quieter overall. That buys
about four extra e-folds of clean growth, and the growth rates settle onto Chen's curve, as this
plot shows. Same physics, much
clearer picture.

---

## B5: Before: the random-start numbers

**Bullets**
- Random start: only ~3 e-folds of growth before saturation
- Fastest wave (m=7): 0.36 ± 0.12 ω_p vs. theory 0.354 ω_p
- Waves m=4–9: simulation/theory = 0.99 ± 0.16; single waves scatter ~±30%
- Sliding the fit window within t = 40–160 (code units) shifts γ by 0.06–0.19 ω_p

**Figure:** `random_start/growth_rate_vs_k.png`

**Speaker notes**
This is where I started. With random starting positions the noise floor was high, so the
fastest wave grew only about three e-folds before trapping stopped it. Over such a short
stretch the fitted growth rate depended on exactly which times I chose, by up to about 0.19
ω_p. On average it still agreed with theory, 0.99 plus or minus 0.16, but any single wave was
uncertain by about 30 percent. That's what motivated the quiet start.

---

## B6: Space-time with the noise made visible

**Bullets**
- Same as slide 10, but each time row is divided by its own rms field
- Shows the pattern even while it is still tiny
- The stripes pick out their positions early and keep them to the end of the run

**Figure:** `spacetime_Ex_normalized.png`

**Speaker notes**
On slide 10 the early field is too weak to see. Here I rescale each moment in time by its own
typical field strength, so the pattern is visible from the start. You can see the stripes pick
out their positions early on and stay there.

---

## B7: Numerical choices

**Bullets**
- Boris push; cloud-in-cell (first-order) particle shape; zigzag charge-conserving current deposit
- Time step: light crosses half a cell per step (CFL = 0.5) → ω_pΔt ≈ 3×10⁻⁴
- Grid: Debye length ≈ 17 cells, so no grid-heating instability
- Random-start run: total energy constant to better than 1 part in 100,000

**Speaker notes**
These are the settings behind both runs; only the starting positions and particle count differ. The time step is set by the speed of light, because
Entity solves the full Maxwell equations, and it ends up far smaller than the plasma needs. The
grid is fine enough to avoid the artificial heating that coarse grids cause.

---

## B8: With ions instead: the Buneman instability

**Bullets**
- Electron beam through ions at rest: the heavy ions respond slowly
- Growth ∝ (m/M)^{1/3}: γ_max ≈ 0.054 ω_pe at kv₀ ≈ ω_pe for hydrogen
- That wave does travel slowly: Re ω ≈ 0.036 ω_pe
- Needs a fixed "return current" in the code; run in progress

**Speaker notes**
If one beam is replaced by ions at rest, you get the Buneman instability. Because ions are
heavy, it grows six to seven times slower, and unlike our case the growing wave has a real
frequency, so it drifts. Simulating it needs an extra fixed current to stop the beam's own
current from pulling it back. That run is still in progress.

---

## Likely Q&A

**Q1. Where does the noise come from, and how did the quiet start reduce it?**
With random positions, the number of particles in a cell fluctuates by about √N, a relative
noise of about 1/√N, and that seeds every wavelength. Evenly spacing the particles, with each
electron on its positive partner, makes the starting charge nearly zero. The velocities are
still random, so some noise comes back, but the effective seed is about 28 times lower. Using
four times as many particles cuts it a further 1.8 times, so my main run starts about 48 times
quieter than the random start.

**Q2. Isn't the quiet start cheating?**
No. The physics (beams, speeds, temperature, grid) is identical. It only
removes counting noise that is much larger than in a real plasma, because a real plasma has
vastly more particles per cell. The instability still has to grow on its own, and it is not
told which wavelength to pick.

**Q3. How did you measure the growth rate, and where do the error bars come from?**
For each wave, I fit straight lines to the log of its amplitude over many short windows
sliding across the straight part (t ≈ 10–22.5/ω_p), and take the median. The error bar is the spread between
windows, so it shows how much the answer depends on which stretch of time I pick.

**Q4. Why does the wave stay in place (Re ω = 0)?**
The two beams are identical except for direction, so there's no preferred direction for the
wave to move. Mathematically the growing root is purely imaginary. In the quiet-start run the
measured real frequency is at most 0.024 ω_p.

**Q5. Why are the grey points (slow growers) so uncertain?**
Theory says the longest waves (m=1–3) and the wave nearest the cutoff (m=11) grow slowly.
Before the fast waves saturate, they have barely risen above the noise, and the strongly growing
waves near the peak also push them around. So their fits are noisy, even with the quiet start.

**Q6. (If asked) Why is the measured growth about 4% below theory?**
Chen's formula assumes perfectly cold beams. My beams have a small thermal spread, 10% of the
beam speed, and warmth smears out the bunching and slows the growth a little. That's the most
plausible reason, though I haven't verified it separately, for example with a colder run.

**Q7. How did you choose the time step?**
Entity solves the full Maxwell equations, so light must not cross more than one cell per step.
I used half a cell per step (CFL = 0.5), which makes ω_pΔt ≈ 3×10⁻⁴, far below the stability
limit of 2 for the particle push.

**Q8. What particle shape did you use?**
Cloud-in-cell, which is first order: each particle's charge is split between the two nearest
grid points according to distance. Smoother shapes reduce noise but cost more. I didn't vary
it.

**Q9. What changes with ions (the Buneman instability)?**
See backup B8: the growth is slower, scaling as (m/M)^{1/3}, and the wave drifts slowly
(Re ω ≈ 0.036 ω_pe) instead of standing still.
