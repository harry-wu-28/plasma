"""
Helper module for reading ADIOS2 BP4 files from the Entity turbulence simulation.

Usage:
    from read_bp import read_fields, read_spectra, read_particles, get_bp_files
"""

import os
import glob
import numpy as np
import adios2


DATA_DIR = "/dartfs-hpc/scratch/f007hd2/turb2d/turbulence"
FIELDS_DIR = os.path.join(DATA_DIR, "fields")
SPECTRA_DIR = os.path.join(DATA_DIR, "spectra")
PARTICLES_DIR = os.path.join(DATA_DIR, "particles")
STATS_FILE = os.path.join(DATA_DIR, "turbulence_stats.csv")


def get_bp_files(subdir):
    """Return sorted list of .bp paths in a subdirectory."""
    pattern = os.path.join(DATA_DIR, subdir, "*.bp")
    return sorted(glob.glob(pattern))


def _open_bp5(path):
    """Return an open ADIOS2 BP5 engine (caller must close it)."""
    adios = adios2.Adios()
    io = adios.declare_io("reader")
    io.set_engine("BP5")
    engine = io.open(path, adios2.Mode.Read)
    return adios, io, engine


_TYPE_MAP = {
    "uint64_t": np.uint64,
    "int64_t":  np.int64,
    "uint32_t": np.uint32,
    "int32_t":  np.int32,
    "double":   np.float64,
    "float":    np.float32,
}


def _numpy_dtype(adios_type):
    return _TYPE_MAP.get(adios_type, np.float64)


def read_scalar(engine, io, name):
    var = io.inquire_variable(name)
    info = io.available_variables()[name]
    dtype = _numpy_dtype(info["Type"])
    buf = np.zeros(1, dtype=dtype)
    engine.get(var, buf)
    engine.perform_gets()
    return buf[0].item()


def read_array(engine, io, name, dtype=None):
    var = io.inquire_variable(name)
    info = io.available_variables()[name]
    shape_str = info["Shape"].strip()
    if "," in shape_str:
        shape = tuple(int(s) for s in shape_str.split(","))
    elif shape_str == "":
        shape = tuple(var.count()) if var.count() else (1,)
    else:
        shape = (int(shape_str),)
    if dtype is None:
        dtype = _numpy_dtype(info["Type"])
    buf = np.zeros(shape, dtype=dtype)
    engine.get(var, buf)
    engine.perform_gets()
    return buf


def read_fields(bp_path, field_names=None):
    """
    Read a fields BP4 file.

    Returns
    -------
    dict with keys:
        'step', 'time', 'x1', 'x2', and each requested field name
        (e.g. 'fB1', 'fB2', 'fB3', 'fE1', ...)
    """
    adios, io, engine = _open_bp5(bp_path)
    engine.begin_step()

    available = io.available_variables()

    # Coordinate arrays
    x1 = read_array(engine, io, "X1")
    x2 = read_array(engine, io, "X2")
    step = int(read_scalar(engine, io, "Step"))
    time = read_scalar(engine, io, "Time")

    result = {"step": step, "time": time, "x1": x1, "x2": x2}

    if field_names is None:
        field_names = [k for k in available if k.startswith("f")]

    for name in field_names:
        if name in available:
            result[name] = read_array(engine, io, name)

    engine.end_step()
    engine.close()
    return result


def read_spectra(bp_path):
    """
    Read a spectra BP4 file.

    Returns
    -------
    dict with keys: 'step', 'time', 'energy_bins', 'sN_1', 'sN_2', 'sEbn'
        energy_bins : midpoints of energy bins (200,)
        sEbn        : bin edges (201,)
        sN_1/sN_2   : particle counts per bin for each species
    """
    adios, io, engine = _open_bp5(bp_path)
    engine.begin_step()

    step = int(read_scalar(engine, io, "Step"))
    time = read_scalar(engine, io, "Time")
    ebn = read_array(engine, io, "sEbn")   # 201 bin edges
    n1 = read_array(engine, io, "sN_1")   # 200 counts
    n2 = read_array(engine, io, "sN_2")

    engine.end_step()
    engine.close()

    energy_mids = 0.5 * (ebn[:-1] + ebn[1:])
    return {
        "step": step,
        "time": time,
        "sEbn": ebn,
        "energy_bins": energy_mids,
        "sN_1": n1,
        "sN_2": n2,
    }


def read_particles(bp_path, species=(1, 2)):
    """
    Read a particles BP4 file.

    Returns
    -------
    dict with keys: 'step', 'time', and per-species:
        'x1_s', 'x2_s', 'u1_s', 'u2_s', 'u3_s', 'w_s'   (s = species index)
    """
    adios, io, engine = _open_bp5(bp_path)
    engine.begin_step()

    step = int(read_scalar(engine, io, "Step"))
    time = read_scalar(engine, io, "Time")
    result = {"step": step, "time": time}

    for s in species:
        result[f"x1_{s}"] = read_array(engine, io, f"pX1_{s}")
        result[f"x2_{s}"] = read_array(engine, io, f"pX2_{s}")
        result[f"u1_{s}"] = read_array(engine, io, f"pU1_{s}")
        result[f"u2_{s}"] = read_array(engine, io, f"pU2_{s}")
        result[f"u3_{s}"] = read_array(engine, io, f"pU3_{s}")
        result[f"w_{s}"] = read_array(engine, io, f"pW_{s}")

    engine.end_step()
    engine.close()
    return result


def gamma_from_u(u1, u2, u3):
    """Lorentz factor from three-velocity components (c=1)."""
    return np.sqrt(1.0 + u1**2 + u2**2 + u3**2)
