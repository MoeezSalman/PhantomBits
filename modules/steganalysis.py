"""
Steganalysis: detect LSB hidden data using the chi-square attack.
"""

from __future__ import annotations
import numpy as np
from PIL import Image
from scipy.stats import chi2

from utils.image_utils import image_to_array


def _chi_square_p(values: np.ndarray) -> float:
    """
    Chi-square test on pairs of values (0,1), (2,3), (4,5) ...
    High p-value (close to 1)  -> pairs are equalised -> LSBs look embedded.
    Low p-value  (close to 0)  -> natural image.
    """
    counts = np.bincount(values, minlength=256).astype(np.float64)
    even = counts[0::2]
    odd = counts[1::2]
    expected = (even + odd) / 2
    mask = expected > 5                      # ignore pairs with too few samples
    if mask.sum() < 2:
        return 0.0
    stat = np.sum((even[mask] - expected[mask]) ** 2 / expected[mask])
    df = int(mask.sum()) - 1
    return float(chi2.sf(stat, df))


def chi_square_attack(image: Image.Image, steps: int = 20) -> dict:
    """
    Run the chi-square test on a growing part of the image.
    PhantomBits embeds from the START of the pixel data, so p-values are high
    at the beginning and drop where the hidden data stops.
    """
    flat = image_to_array(image).reshape(-1)
    n = len(flat)
    start = min(n, 5000)
    sizes = np.unique(np.geomspace(start, n, steps).astype(int))
    p_values = [_chi_square_p(flat[:s]) for s in sizes]
    return {
        "fractions": (sizes / n).tolist(),
        "p_values": p_values,
        "max_p": float(max(p_values)),
        "p_overall": float(p_values[-1]),
    }


def is_suspicious(result: dict, threshold: float = 0.5) -> bool:
    return result["max_p"] >= threshold

# ---------------------------------------------------------------------------
# RS analysis (Fridrich, Goljan & Du) – estimates the embedding rate
# ---------------------------------------------------------------------------
_MASK = np.array([0, 1, 1, 0])


def _smoothness(groups: np.ndarray) -> np.ndarray:
    """Discrimination function: sum of absolute neighbour differences."""
    return np.abs(np.diff(groups, axis=1)).sum(axis=1)


def _flip(groups: np.ndarray, negative: bool) -> np.ndarray:
    """F1 (0<->1, 2<->3 ...) or F-1 (-1<->0, 1<->2 ...) on the masked positions."""
    out = groups.copy()
    cols = _MASK == 1
    if negative:
        out[:, cols] = ((out[:, cols] + 1) ^ 1) - 1
    else:
        out[:, cols] = out[:, cols] ^ 1
    return out


def _rs_diff(groups: np.ndarray, negative: bool) -> float:
    base = _smoothness(groups)
    flipped = _smoothness(_flip(groups, negative))
    return float(((flipped > base).mean()) - ((flipped < base).mean()))   # R - S


def _rs_rate(channel: np.ndarray) -> float:
    """Estimated fraction (0-1) of LSBs that were used for hiding."""
    n = (len(channel) // 4) * 4
    if n < 400:
        return 0.0
    x = channel[:n].astype(np.int32)
    g = x.reshape(-1, 4)
    g_flip = (x ^ 1).reshape(-1, 4)

    d0   = _rs_diff(g, False)        # R_M - S_M   at p/2
    d_0  = _rs_diff(g, True)         # R_-M - S_-M at p/2
    d1   = _rs_diff(g_flip, False)   # at 1 - p/2
    d_1  = _rs_diff(g_flip, True)

    a = 2 * (d1 + d0)
    b = d_0 - d_1 - d1 - 3 * d0
    c = d0 - d_0
    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return 0.0
        z = -c / b
    else:
        disc = b * b - 4 * a * c
        if disc < 0:
            return 0.0
        roots = [(-b + disc ** 0.5) / (2 * a), (-b - disc ** 0.5) / (2 * a)]
        z = min(roots, key=abs)
    if abs(z - 0.5) < 1e-12:
        return 0.0
    p = z / (z - 0.5)
    return float(min(max(p, 0.0), 1.0))


def rs_analysis(image: Image.Image, steps: int = 12) -> dict:
    """
    Run RS analysis on a growing top part of the image (PhantomBits embeds
    from the start). Returns the estimated embedding rate for each part.
    """
    arr = image_to_array(image)
    npix = arr.shape[0] * arr.shape[1]
    start = min(npix, 3000)
    sizes = np.unique(np.geomspace(start, npix, steps).astype(int))
    rates = []
    for s in sizes:
        per_channel = [_rs_rate(arr[:, :, c].reshape(-1)[:s]) for c in range(3)]
        rates.append(float(np.mean(per_channel)))
    return {
        "fractions": (sizes / npix).tolist(),
        "rates": rates,
        "max_rate": float(max(rates)),
    }

# ---------------------------------------------------------------------------
# Header check – looks for the PhantomBits 32-bit length header
# ---------------------------------------------------------------------------
_MIN_PAYLOAD = 16 + 12 + 16        # salt + nonce + GCM tag = smallest valid payload


def header_check(image: Image.Image) -> dict:
    """
    PhantomBits writes a 32-bit length header in the first LSBs.
    In a normal image those bits decode to a random number, which is almost
    never a valid length. A valid length means a PhantomBits message is present.
    """
    from utils.image_utils import max_payload_bytes

    flat = image_to_array(image).reshape(-1)
    bits = (flat[:32] & 1).astype(np.uint8)
    length = int.from_bytes(np.packbits(bits).tobytes(), byteorder="big")
    found = _MIN_PAYLOAD <= length <= max_payload_bytes(image)
    return {"found": bool(found), "length": length if found else None}