# Two-stream talk: slide text and speaker notes

10-minute talk + 10 minutes Q&A. Source: `paper/twostream_electron_electron.tex` and the
baseline run (`twostream/runs/baseline`, CPU job 11088180). The figures are in `talk/figures/`.

**Units used on every slide (same as Chen and the figures):** ω_p is the plasma frequency of
*all* the electrons (both beams together), so ω_p² = n e²/(ε₀ m) with n = total electron
density. The wavenumber is written as kv₀/ω_p, and time as t in units of 1/ω_p.
(The written report uses ω_b, the frequency of one beam: ω_p = √2 ω_b.)

Each slide has a title, at most 4 bullets, the figure to show, and about 1 minute of speaker
notes in plain English.

---

## Slide 1: Can a computer get the textbook answer? Simulating the two-stream instability

**Bullets**
- Harry Wu, [course name], [date]
- Particle-in-cell (PIC) simulation with the Entity code

**Figure:** none (or a small phase_space.png panel as background art)

**Speaker notes**
Hi, I'm Harry. In class we derived the two-stream instability with pen and paper. For this
project I asked a simple question: if I put the same setup into a real plasma simulation code,
does it give the same answer? The code is called Entity. It's a particle-in-cell, or PIC, code
used for research in plasma astrophysics. I'll explain what the two-stream instability is, how
a PIC code works, and then compare the simulation to Chen's textbook predictions: how fast
the wave grows, which wavelength grows fastest, and what the electrons look like once the wave
gets big. The short answer is that the simulation reproduces the theory well, and I'll show
where it works and where it struggles.

---

## Slide 2: What is the two-stream instability?

**Bullets**
- Two electron beams pass through each other at ±v₀
- A small density ripple makes an electric field
- The field bunches the electrons → a bigger ripple → a bigger field
- Result: the ripple grows exponentially, ∝ e^{γt}

**Figure:** none, or a simple cartoon of two arrows and a wavy density line

**Speaker notes**
Picture two streams of electrons going opposite ways, with a fixed background of positive
charge so the plasma is neutral overall. If everything is perfectly uniform, nothing happens.
But real plasmas are never perfectly uniform. Say there's a tiny ripple, with slightly more
electrons in one place. That ripple makes an electric field. The field speeds up some
electrons and slows down others, and that makes them pile up even more where they were
already piled up. More bunching means a stronger field, which means more bunching. That's a
feedback loop, and it makes the ripple grow exponentially. This is what we call an
instability. The number we care about is the growth rate γ: how fast the ripple grows.

---

## Slide 3: Theory: Chen's graphical method

**Bullets**
- Dispersion relation: 1 = ½ω_p² [1/(ω − kv₀)² + 1/(ω + kv₀)²]
- Short waves: 4 real roots → the wave just oscillates
- Long waves (kv₀ < ω_p): 2 complex roots → the wave grows
- Fastest growth: γ_max = ω_p/(2√2) ≈ 0.354 ω_p at kv₀ ≈ 0.61 ω_p

**Figure:** `dispersion_stable_unstable.png`

**Speaker notes**
From the cold-fluid equations (continuity, Newton's law, and Gauss's law) you get this
dispersion relation. It tells you which frequencies ω go with each wavenumber k. Chen solves
it graphically: plot the right-hand side and see where it crosses one. On the left, for a short
wave, the curve crosses one four times, so all four roots are real, and the wave just
oscillates. On the right, for a longer wave, it only crosses twice. The equation has four roots,
so the missing two must be complex, and a complex frequency means exponential growth. Every
wave with kv₀ below ω_p is unstable. Solving exactly, the fastest wave grows at ω_p over 2√2,
about 0.354 ω_p, at kv₀ ≈ 0.61 ω_p. These are the numbers I'll test.

---

## Slide 4: How a particle-in-cell code works

**Bullets**
- Macroparticles: each one stands for many electrons (same charge-to-mass ratio)
- Fields live on a grid; particles move freely between grid points
- Each time step: deposit current → solve for fields → interpolate fields to particles → push particles
- Repeat ~250,000 times

**Figure:** a loop diagram of the four steps (deposit → field solve → interpolate → push)

**Speaker notes**
A real plasma has far too many electrons to simulate one by one. So a PIC code uses
macroparticles. Each one represents a huge number of real electrons, but it has the same
charge-to-mass ratio, so it moves exactly like a single electron would. The electric field is
stored only at points on a grid. Every time step does four things. First, each particle's
motion is turned into current on the nearby grid points. Second, the code updates the electric
field from that current. Third, it reads the field back at each particle's position. Fourth, it
uses Newton's law to push each particle to a new velocity and position. Then it repeats. My
run did this about 250,000 times, and it took 52 minutes on 16 CPU cores.

---

## Slide 5: The simulation setup

**Bullets**
- 1D box with periodic edges (a particle leaving the right side comes back on the left)
- Two equal electron beams at ±0.1c on a fixed positive background
- No wave is added by hand: random particle positions supply the first ripple

**Table**

| Setting | Value |
|---|---|
| Beams | 2 electron beams, ±0.1c, equal density; thermal spread 0.01c |
| Box | length ≈ 7 c/ω_p, holds ~7 wavelengths of the fastest wave |
| Grid | 12,288 cells; Debye length ≈ 17 cells |
| Particles | 4 per cell per beam (~49,000 per beam) |
| Time step and numerics | ω_pΔt ≈ 3×10⁻⁴; Boris push, cloud-in-cell shape, zigzag current deposit |

**Figure:** none (the table is the content)

**Speaker notes**
Here's the setup. It's one-dimensional, so everything moves along x, and the box wraps around
at the edges. There are two electron beams moving at a tenth of the speed of light in opposite
directions. The positive background is made of particles that are held fixed, standing in for
ions. The beams are almost cold: the random thermal speed is only 10% of the beam speed, which
is close to Chen's cold-beam assumption. The box fits about seven wavelengths of the fastest
wave. The grid is very fine, about 17 cells per Debye length, which avoids an artificial
heating problem PIC codes have when the grid is too coarse. One important detail: I don't add
any wave by hand. The particles start at random positions, and that randomness is the seed.

---

## Slide 6: What the electrons do (phase space)

**Bullets**
- Each dot: one macroparticle's position and velocity
- Start: two flat, separate beams
- Growth: the beams develop ripples
- Late: the beams merge into swirling vortices (trapped electrons)

**Figure:** `phase_space.png` (t = 0, 10, 13 /ω_p)

**Speaker notes**
This is phase space: horizontal is position, vertical is velocity, and each dot is one
macroparticle. Blue is the beam going right, red is the beam going left. At the start you see
two flat lines at plus and minus 0.1c, just two uniform beams. By time 10 over ω_p the beams have
developed ripples. That's the instability: electrons are being sped up and slowed down by the
growing wave. By time 13 the ripples are so big that the beams overlap and curl into
vortices. Those are electrons that are trapped inside the wave's potential wells. This is the
nonlinear stage, where the simple linear theory stops applying and the growth stops.

---

## Slide 7: Growth of the fastest wave vs. prediction

**Bullets**
- Take the Fourier transform of E(x) to get the amplitude of each wave
- On a log scale, exponential growth is a straight line
- Dashed line: theory slope, not fitted, only started at the same point
- Matches until the wave saturates at t ≈ 13/ω_p

**Figure:** `growth_fastest_mode.png`

**Speaker notes**
To measure the growth rate, I take the electric field along the box and Fourier transform it.
That splits it into individual waves, and I follow the amplitude of each one over time. This
plot is the wave closest to the fastest-growing one. The vertical axis is logarithmic, so
exponential growth shows up as a straight line. The dashed line is Chen's prediction. I didn't
fit it to the data; I just started it at the same point and let it run with the theoretical
slope. In the shaded region the simulation follows it closely. Before that, the field is
still settling down from the random starting noise. After about 13 over ω_p, the wave stops
growing, because it has trapped the electrons, as in the vortices on the previous slide.

---

## Slide 8: Growth rate at every wavelength

**Bullets**
- Each dot: the measured growth rate of one wave in the box
- Fastest wave: simulation 0.352 ± 0.007 ω_p vs. theory 0.354 ω_p
- Measured at kv₀/ω_p = 0.624 (the box wave closest to the theory peak at 0.612)
- Away from the peak, the points scatter by roughly ±20%

**Figure:** `growth_rate_vs_k.png`

**Speaker notes**
Now I do the same measurement for every wave the box allows and compare to the full theory
curve. The black curve is Chen's prediction, and the dots are the simulation. The key result
is the fastest wave. The simulation gives 0.352 times ω_p, and theory says 0.354. That's less
than 1% off. Because the box is periodic, only certain wavelengths fit, so the closest one is
at 0.624 instead of exactly 0.612. Away from the peak the agreement is rougher, about plus or
minus 20%. The points at the far edges, the very long and very short waves, don't match well.
Those waves grow slowly, so they're buried in noise and get pushed around by the fast waves
before they can show clean growth.

---

## Slide 9: After growth stops: trapping and the plateau

**Bullets**
- Simulated electrons sit on the trapped orbits predicted from the measured potential (Chen Fig. 7.12)
- The velocity distribution starts with two separate peaks…
- …and flattens into a plateau, removing the beam energy that drove the wave (Chen Fig. 7.19)

**Figure:** `trapping_separatrix.png` (left) and `fv_plateau.png` (right)

**Speaker notes**
Linear theory stops when the wave gets big, but Chen also describes what happens next, and the
simulation shows that too. On the left, I took the electric potential from the simulation and
drew the orbits an electron should follow in it. The red line is the boundary between trapped
and passing electrons. The simulated electrons, in grey, sit right on those orbits. On the
right is the velocity distribution. It starts as two sharp peaks, one for each beam. By the end
it has flattened into a broad plateau. The two beams have mixed, so there's no more free
energy to drive the instability. This is what Chen sketches in Figure 7.19, and the simulation
reproduces it.

---

## Slide 10: Limits of PIC, and conclusion

**Bullets**
- PIC reproduces Chen: fastest growth rate within 1%, trapping, and the plateau
- Limit 1: few particles → noisy start → short clean growth window
- Limit 2: slow-growing waves are hard to measure; only waves that fit the box exist
- Energy is conserved to better than 1 part in 100,000 over the run

**Figure:** none, or repeat the growth-rate plot small

**Speaker notes**
To sum up: a particle-in-cell simulation reproduces the textbook two-stream instability. The
fastest growth rate matches to better than 1%, the wave doesn't oscillate, just as theory
predicts, and the nonlinear stage shows the trapping and plateau that Chen describes. There are
limits. With only four particles per cell per beam, the starting noise is large, so the wave
has only a short window of clean exponential growth before it saturates. That's why the
slow-growing waves are hard to measure. Also, a periodic box only allows certain wavelengths.
And PIC isn't perfect at conserving energy, though here the total energy stayed constant to
better than one part in 100,000. Thank you, and I'm happy to take questions.

---

## Likely Q&A

**Q1. Why is the simulation noisy, and how does that depend on the number of particles?**
Each cell holds only a few particles at random positions, so the count in a cell fluctuates by
about √N. The relative noise is about 1/√N, here 1/√4 = 50% per beam per cell. More particles
would give a quieter start, a longer window of clean growth, and better measurements of the
slow waves. The cost is that the run takes proportionally longer.

**Q2. Why did you fit only between t ≈ 4 and 10/ω_p?**
Before about 4/ω_p, the field is still settling from the random starting positions, and all
waves jump to a noise level. After about 10/ω_p, the wave is big enough that nonlinear effects
(trapping, waves interacting) bend the curve over. The straight-line exponential stage is in
between. In code units the window is t = 60–140, and saturation is at t = 188.

**Q3. Why is the real part of the frequency zero, so the wave doesn't move?**
The two beams are identical except for direction, so the setup has no preferred direction and
the wave can't travel either way. It just grows in place. Mathematically, the growing root is
purely imaginary. The simulation agrees: the measured real frequency is near zero, within about
0.07 ω_p.

**Q4. How did you choose the time step?**
Entity solves the full Maxwell equations, so light must not cross more than one cell per step.
I used half a cell per step (CFL = 0.5). That makes the step tiny compared with the plasma
oscillation, ω_pΔt ≈ 3×10⁻⁴, far below the stability limit of 2 for the leapfrog push. The
light-speed rule, not the plasma, sets the step.

**Q5. What particle shape did you use, and why does it matter?**
Cloud-in-cell, which is first order: each particle's charge is split between the two nearest
grid points according to distance. Smoother, higher-order shapes reduce noise but cost more
per particle. I didn't vary the shape. This project shows that one reasonable setting gets the
right answer; it doesn't compare settings.

**Q6. What would change with ions instead of a second electron beam (the Buneman instability)?**
If an electron beam streams through ions at rest, the heavy ions respond slowly. The growth
rate scales like (m/M)^{1/3}: for hydrogen, γ_max ≈ 0.054 ω_pe at kv₀ ≈ ω_pe, about 6–7 times
slower than here. The wave also oscillates (Re ω ≈ 0.036 ω_pe) instead of standing still. In
the code it needs an extra trick, a fixed "return current", to keep the beam from being pulled
back by its own current. I have that run going, but it isn't part of this talk.

**Q7. Why do the points at the edges of the γ(k) plot disagree?**
Those waves grow slowly, so in the short time before saturation they barely rise above the
noise. They also get driven by the strongly growing waves near the peak (nonlinear mode
coupling). Their measured "growth" reflects noise and coupling more than their own linear
growth.

**Q8. How do you know the simulation isn't just heating up artificially?**
Two checks. The grid resolves the Debye length well (about 17 cells per Debye length), so the
known grid-heating instability shouldn't occur. And the total energy (particles plus field)
stays constant to better than 1 part in 100,000 over the whole run.
