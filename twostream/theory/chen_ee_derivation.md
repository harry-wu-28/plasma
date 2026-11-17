# Chen §6.6 redone for two electron streams, and checked against the simulation

Chen (*Introduction to Plasma Physics and Controlled Fusion*, 3rd ed., §6.6, pp. 198–201)
derives the two-stream instability for **cold ions at rest + a cold electron stream**
(Eqs. 6.19–6.35, Figs. 6.8–6.9; the "Buneman" instability). His Problem 6.6 asks for the
case simulated here: **two cold electron streams with equal and opposite v₀, each of density
n₀/2, in a fixed ion background**. Below, Chen's steps are repeated one for one for that
case (primed numbers = the electron–electron version of his equation), then each result is
compared with the Entity baseline run (CPU job 11088180, 2026-11-16).

Figures: `analysis/chen_ee.py RUN --out DIR` (here `runs/baseline/plots/chen/`).
Numbers: `chen_ee_comparison.csv` in the same folder.

## 1. Algebra (Chen's notation)

ω_p is the plasma frequency of **all** the electrons, ω_p² = n₀e²/ε₀m. Each stream alone
has ω_b² = ω_p²/2.

**Equations of motion** (Chen 6.19–6.20). Both species are now electrons, both drift:

$$mn_0/2\left[\frac{\partial v_1}{\partial t}+v_0\frac{\partial v_1}{\partial x}\right]=-e\,\frac{n_0}{2}E_1 \qquad (6.19')$$
$$mn_0/2\left[\frac{\partial v_2}{\partial t}-v_0\frac{\partial v_2}{\partial x}\right]=-e\,\frac{n_0}{2}E_1 \qquad (6.20')$$

With $E_1 = Ee^{i(kx-\omega t)}$ (6.21), each stream sees its own Doppler-shifted frequency:

$$v_1=-\frac{ie}{m}\frac{E}{\omega-kv_0},\qquad v_2=-\frac{ie}{m}\frac{E}{\omega+kv_0} \qquad (6.22',\,6.23')$$

(Chen's ion equation 6.22 has $\omega$ alone because his ions do not drift; here *both*
denominators are shifted.)

**Continuity** (Chen 6.24–6.27), $\partial n_j/\partial t + (n_0/2)\,\partial v_j/\partial x + v_{0j}\,\partial n_j/\partial x = 0$:

$$n_1=\frac{n_0}{2}\frac{k\,v_1}{\omega-kv_0}=-\frac{ie\,(n_0/2)\,k}{m(\omega-kv_0)^2}E,\qquad
n_2=-\frac{ie\,(n_0/2)\,k}{m(\omega+kv_0)^2}E \qquad (6.27')$$

**Poisson** (Chen 6.28–6.29). The ions are fixed, so only electrons perturb the charge:

$$ik\varepsilon_0E=-e(n_1+n_2)=\frac{ie^2n_0k}{2m}E\left[\frac{1}{(\omega-kv_0)^2}+\frac{1}{(\omega+kv_0)^2}\right] \qquad (6.29')$$

**Dispersion relation** (Chen 6.30), dividing by $ik\varepsilon_0E$:

$$1=\frac{\omega_p^2}{2}\left[\frac{1}{(\omega-kv_0)^2}+\frac{1}{(\omega+kv_0)^2}\right] \qquad (6.30')$$

Compare Chen's $1=\omega_p^2\left[\frac{m/M}{\omega^2}+\frac{1}{(\omega-kv_0)^2}\right]$: the ion
term $(m/M)/\omega^2$ (tiny weight, pole at ω = 0) is replaced by a second electron term of
equal weight with its pole at ω = −kv₀.

**Graphical analysis** (Chen 6.33–6.34, Figs. 6.8/6.9). With $x\equiv\omega/\omega_p$,
$y\equiv kv_0/\omega_p$:

$$1=\tfrac12\left[\frac{1}{(x-y)^2}+\frac{1}{(x+y)^2}\right]\equiv F(x,y) \qquad (6.34')$$

F is even in x, with poles at x = ±y. Outside the poles F falls monotonically from ∞ to 0,
so there is always one real root on each side. Between the poles F has its minimum at
x = 0, where **F(0, y) = 1/y²**. Then:

- y > 1: the minimum is below 1, giving two more crossings: **4 real roots, stable**
  (the analog of Chen's Fig. 6.8).
- y < 1: the minimum is above 1, so the curve misses the line: **2 real + 2 complex roots,
  unstable** (the analog of Fig. 6.9).

So the instability condition is exactly **kv₀ < ω_p**. As in Chen's case, for any v₀ the
long waves are unstable.
→ `fig6_8_6_9.png` (top: Chen's ion–electron Figs. 6.8/6.9 redrawn with m/M = 1/1836;
bottom: electron–electron).

**Exact solution** (where Chen stops at "≈", Eq. 6.35). Because F is even, the quartic is a
quadratic in X = x². Multiply by $(x^2-y^2)^2$, using
$\tfrac12[(x+y)^2+(x-y)^2]=x^2+y^2$:

$$X^2-(2y^2+1)X+y^4-y^2=0\;\Rightarrow\; x^2=y^2+\tfrac12\pm\tfrac12\sqrt{1+8y^2}$$

The product of the two X roots is $y^2(y^2-1)$, so the minus root is negative exactly when
y < 1, which confirms the graphical result. That root gives $x=\pm i\,(\ldots)$: the
unstable mode has **Re ω = 0 exactly**. It is purely growing and stands still in the lab
frame.

$$\frac{\gamma}{\omega_p}=\left[\tfrac12\sqrt{1+8y^2}-y^2-\tfrac12\right]^{1/2} \qquad (6.35')$$

Setting $d(\gamma^2)/d(y^2)=0$ gives $2/\sqrt{1+8y^2}=1$, so $y^2=3/8$, and

$$\boxed{\;\gamma_{\max}=\frac{\omega_p}{2\sqrt2}\approx0.354\,\omega_p\ \ \text{at}\ \ kv_0=\sqrt{3/8}\,\omega_p\;}\quad\text{(Problem 6.6b)}$$

In beam units, $\gamma_{\max}=\omega_b/2$ at $kv_0=(\sqrt3/2)\omega_b$, with the cutoff at
$kv_0=\sqrt2\,\omega_b$ (paper Eq. gmax).

For contrast, Chen's ion–electron Eq. 6.35 gives Im(ω/ω_p) ≈ (m/M)^{1/3} = 0.082. The
largest imaginary root of his Eq. 6.30 is actually 0.054, the standard Buneman value
(√3/2)(m/2M)^{1/3} = 0.056. The electron–electron case grows about 6.5× faster, because
both species respond on the electron time scale. → `roots.png`, grey curve.

**Eigenvector** (from 6.27′, beyond Chen's text). On the growing root ω = iγ, define
tan α = γ/kv₀. Then:

- $n_1/n_2=(\omega+kv_0)^2/(\omega-kv_0)^2$, so **|n₁| = |n₂|** and **arg(n₁/n₂) = 4α**.
  The two beams bunch equally hard, offset in space by the phase 4α.
- arg(n₁/E) = 2α − 90°, arg(n₂/E) = −2α − 90°. The total charge n₁ + n₂ sits at −90° from E,
  as Poisson requires.
- $|n_j|/(n_0/2)=e\,k\,|E|\,/\,[m(\gamma^2+k^2v_0^2)]$.

**Physical picture** (Chen p. 201, adapted). Each stream carries Doppler-shifted
space-charge oscillations, ω = kv_{0j} ± ω_b. The slow wave of the +v₀ stream (ω = kv₀ − ω_b)
and the slow wave of the −v₀ stream (ω = −kv₀ + ω_b) coincide at ω = 0 when kv₀ ≈ ω_b. That
is the same "two frequencies coincide in the lab frame" mechanism Chen describes for ions
and electrons, with the stream oscillations playing the role of his ion oscillations. Near
that point one of the pair carries negative wave energy, so both can grow while total
energy is conserved. The unstable band kv₀ < √2 ω_b brackets kv₀ = ω_b.

**Nonlinear stage** (Chen §7.5, Figs. 7.10–7.13, 7.19). Because Re ω = 0, the lab frame
*is* the wave frame. Electrons with small velocity are trapped in the potential troughs
(Fig. 7.11) and circulate on closed orbits inside the separatrix (Fig. 7.12). The
initially empty gap near v = 0 is twisted into "water bags" (Fig. 7.13). f(v), which starts
double-humped with v_φ = 0 at its minimum, as Chen's instability criterion requires
(Fig. 7.19), relaxes toward a plateau. Growth stops roughly when the bounce frequency
$\omega_B=\sqrt{ekE/m}$ reaches γ.

## 2. Mapping to the simulation (Entity code units)

| Chen | this run |
|---|---|
| n₀/2 per stream | n_b = 0.25 n0 (`densities = [0.5, 0.5]` is the *pair* total) |
| ω_b, ω_p = √2 ω_b | ω_b = √n_b / skindepth0 = 0.0500; relativistic longitudinal mass γ₀³m → ω_b,eff = 0.0496, ω_p,eff = 0.0702 |
| v₀ | u₀ = 0.1 → v₀ = 0.0995 c |
| y = 1 cutoff | k = 0.705 (box modes m ≤ 11, L = 100) |
| y = √(3/8) fastest | k = 0.432, λ = 14.5 (m ≈ 7) |
| e E/m (force) | (q/m) E / larmor0 |
| ε₀ ∂E/∂x = ρ | ∂E/∂x = (larmor0/skindepth0²) ρ: measured coefficient 1.04–1.06 vs 1 (`fig chen4` Poisson check) |

## 3. Comparison with the run

Linear window t = 60–140 (field energy grows cleanly over t ≈ 40–150; first saturation at
t ≈ 180). Eigenvector quantities are averaged over t = 100–140. Measured angles are shown on
the 360° branch nearest the theory value.

| m | y | γ/ω_p meas | γ/ω_p theory | ratio | Re x meas | arg(n₁/n₂) meas | 4α | \|n/n_b\|/\|E\| meas | theory |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.089 | 0.321 | 0.088 | 3.66 | −1.18 | 269° | 178° | 10.1 | 8.0 |
| 2 | 0.178 | 0.270 | 0.168 | 1.61 | 0.23 | 204° | 173° | 3.1 | 4.2 |
| 3 | 0.267 | 0.470 | 0.235 | 2.00 | −0.02 | 190° | 165° | 2.9 | 3.0 |
| 4 | 0.356 | 0.339 | 0.288 | 1.18 | −0.07 | 176° | 156° | 2.41 | 2.40 |
| 5 | 0.445 | 0.374 | 0.325 | 1.15 | 0.07 | 159° | 145° | 2.28 | 2.07 |
| 6 | 0.534 | 0.288 | 0.347 | 0.83 | −0.05 | 138° | 132° | 2.11 | 1.86 |
| **7** | **0.624** | **0.352** | **0.353** | **1.00** | **−0.00** | **129°** | **118°** | **1.89** | **1.71** |
| 8 | 0.713 | 0.405 | 0.342 | 1.18 | −0.01 | 111° | 103° | 1.68 | 1.61 |
| 9 | 0.802 | 0.321 | 0.311 | 1.04 | −0.04 | 107° | 85° | 1.71 | 1.53 |
| 10 | 0.891 | 0.348 | 0.249 | 1.40 | −0.06 | 88° | 62° | 1.60 | 1.47 |
| 11 | 0.980 | 0.281 | 0.114 | 2.46 | 0.02 | 65° | 27° | 1.52 | 1.42 |

**What agrees** (core band 0.3 < y < 0.95, m = 4–10):

- **Growth rate:** the mean measured/theory ratio is 1.11 ± 0.17. The fastest mode, m = 7
  at y = 0.624 (theory: y = 0.612), grows at 0.352 ω_p against 1/(2√2) = 0.354.
  Forward-propagating the measured t = 60 amplitudes with the analytic γ(k), with no fitting,
  tracks |E_m(t)| for m = 5–8 through the linear phase (`growth.png`).
- **Re ω = 0:** the measured |Re x| ≤ 0.07, while the stream Doppler shift y is 0.36–0.89.
  The modes do not propagate, as the even F(x, y) requires (`roots.png`).
- **Cutoff y = 1:** modes with y > 1 do not grow during the linear phase. They rise only
  after t ≈ 120, through nonlinear coupling (`growth.png`, last panel).
- **Eigenvector:**
  - The bunching amplitude per unit field matches 6.27′ to 0–15%.
  - |n₁| ≈ |n₂| (the two beams' points overlie each other).
  - The phases of each beam's bunch relative to E follow 2α − 90° and −2α − 90° to within
    about 5–15° (`eigenvector.png`).
- **Trapping:**
  - At first saturation (t = 180, dominant m = 7), ω_B/γ = 1.18, i.e. growth stops when the
    bounce frequency reaches the growth rate.
  - The separatrix computed from the *measured* potential encloses the simulated vortices
    (`fig7_11_7_12.png`).
  - The empty gap twists into water bags as in Chen's Fig. 7.13 (`fig7_13.png`).
  - f(v) flattens to a plateau (`fig7_19.png`).

**What does not:**

- **Inter-beam phase:** arg(n₁/n₂) runs 10–25° above 4α across the core. By t = 100–140 the
  bunching is already δn/n_b ≈ 0.5–1 (`chen4_bunching.png`), outside strict linearity. Thermal
  spread (T = 1e-4) is a smaller correction. Measuring earlier needs more particles per cell.
- **Long waves (m = 1–3) and the band edges (m = 10–11):** these grow only a few e-folds
  above the shot noise at ppc0 = 16 (4 per cell per beam), so their fits are noise-dominated,
  as the README warns. The ppc64/ppc256 scan runs are the test of this.
