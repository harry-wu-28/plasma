# Figures

Drop finished figures here using the filenames below. Each report shows a labelled
placeholder box for any file that is missing, so it compiles either way.
Prefix `ee_` = electron-electron report, `ei_` = electron-ion (Buneman) report.

| File | Report | Content |
|---|---|---|
| `ee_growth_mode.pdf` | electron-electron | `ln|E_k(t)|` for the fastest-growing mode, with the linear-phase fit |
| `ee_gamma_vs_k.pdf` | electron-electron | measured γ(k)/ω_b vs. k v0/ω_b, against the cold-beam dispersion relation |
| `ei_growth_mode.pdf` | electron-ion | `ln|E_k(t)|` for mode m = 16, with the linear-phase fit |
| `ei_dispersion.pdf` | electron-ion | measured γ/ω_pe and Re ω/ω_pe per box mode vs. k v0/ω_pe, against the exact quartic roots |

Generate figures as vector PDF (matplotlib `savefig("x.pdf")`), sized for a 3.4 in column.
