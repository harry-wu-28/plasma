

import numpy as np

# ── Shared simulation parameters (match turb_2d_GPU.toml) ────────────────────
L      = 128.0   # domain side length (code units)
D_SKIN = 1.0     # electron skin depth d_e  (= skindepth0 = 1)


def isotropic_mag_spectrum(fields, L=L, D_SKIN=D_SKIN):
    """
    Isotropic shell-averaged magnetic energy spectral density E(k).

    Parameters
    ----------
    fields : dict
        Must contain 'fB1', 'fB2', 'fB3' as 2-D (nx, ny) arrays.
    L : float
        Domain side length (code units, square domain assumed).
    D_SKIN : float
        Electron skin depth d_e.  Returned kd is in k * d_e units.

    Returns
    -------
    kd     : ndarray  (n_shells,)
        Shell centres in k * d_e units, kd[n] = (n+1) * dk_fund * D_SKIN.
    E_k    : ndarray  (n_shells,)
        Spectral energy density E(k) = E_shell / dk_fund.
        Kolmogorov inertial range: E_k ∝ k^{-5/3}.
    B_rms  : ndarray  (n_shells,)
        Per-mode RMS field: sqrt(2 * E_shell / nmodes).
    nmodes : ndarray  (n_shells,)
        Number of Fourier modes per shell (diagnostic).
    """
    b1 = fields["fB1"].astype(np.float64)
    b2 = fields["fB2"].astype(np.float64)
    b3 = fields["fB3"].astype(np.float64)
    nx, ny = b1.shape
    dx = L / nx
    dy = L / ny

    # Per-mode energy (Parseval-normalised so sum(Emag) = 0.5 * <B²>)
    Emag = 0.5 * (
        np.abs(np.fft.fft2(b1))**2 +
        np.abs(np.fft.fft2(b2))**2 +
        np.abs(np.fft.fft2(b3))**2
    ) / float(nx * ny)**2

    # Dimensionless shell radius r = |k| / dk_fund = sqrt(i² + j²) for integer indices
    dk_fund = 2 * np.pi / L
    kx      = 2 * np.pi * np.fft.fftfreq(nx, d=dx)
    ky      = 2 * np.pi * np.fft.fftfreq(ny, d=dy)
    KX, KY  = np.meshgrid(kx, ky, indexing="ij")
    r       = np.sqrt(KX**2 + KY**2) / dk_fund

    # Integer shell assignment: each mode → nearest integer shell
    # Limit to the inscribed circle to exclude aliased corner modes
    r_max  = min(nx, ny) / 2
    n_idx  = np.round(r).astype(int).ravel()
    E_flat = Emag.ravel()
    valid  = (n_idx >= 1) & (n_idx <= int(r_max))

    n_shells = int(r_max)
    E_shell  = np.zeros(n_shells + 1)
    nmodes   = np.zeros(n_shells + 1)
    np.add.at(E_shell, n_idx[valid], E_flat[valid])
    np.add.at(nmodes,  n_idx[valid], 1.0)

    # Shells 1…n_shells (exclude n=0 DC mode)
    shells  = np.arange(1, n_shells + 1)
    kd      = shells * dk_fund * D_SKIN
    E_k     = E_shell[1:] / dk_fund          # spectral density per unit k
    B_rms   = np.sqrt(2.0 * E_shell[1:] / np.maximum(nmodes[1:], 1.0))

    return kd, E_k, B_rms, nmodes[1:]


def kolmogorov_ref(kd, E_k, anchor_frac=0.5):
    """
    Compute a k^{-5/3} reference line anchored to the spectrum.

    The anchor bin is chosen at `anchor_frac` along the populated k range
    (default 0.5 = midpoint), so the reference passes through the data.

    Parameters
    ----------
    kd, E_k     : arrays returned by isotropic_mag_spectrum
    anchor_frac : float in [0, 1]

    Returns
    -------
    k_ref, E_ref : arrays for the reference curve, or (None, None) if the
                   spectrum has fewer than 2 valid points.
    """
    mask = (kd > 0) & (E_k > 0) & np.isfinite(E_k)
    if mask.sum() < 2:
        return None, None
    kd_v  = kd[mask]
    Ek_v  = E_k[mask]
    i_anc = int(np.clip(len(kd_v) * anchor_frac, 0, len(kd_v) - 1))
    k_ref = np.logspace(np.log10(kd_v[0]), np.log10(kd_v[-1]), 80)
    E_ref = Ek_v[i_anc] * (k_ref / kd_v[i_anc])**(-5 / 3)
    return k_ref, E_ref
