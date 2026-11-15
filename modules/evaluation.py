"""
Performance evaluation: how invisible is the hiding, and can it be detected?
"""

from __future__ import annotations
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from modules.steganography import encode_message
from modules.steganalysis import rs_analysis, header_check
from utils.image_utils import image_to_array, max_payload_bytes, calculate_psnr

RS_THRESHOLD = 0.30     # same threshold the Image Analysis page uses


def quality_metrics(cover: Image.Image, stego: Image.Image) -> dict:
    """Compare the original and the stego image."""
    a = image_to_array(cover).astype(np.float64)
    b = image_to_array(stego).astype(np.float64)
    mse = float(np.mean((a - b) ** 2))
    psnr = 99.0 if mse == 0 else min(calculate_psnr(cover, stego), 99.0)
    ssim = float(structural_similarity(
        image_to_array(cover), image_to_array(stego), channel_axis=2, data_range=255
    ))
    changed = float(np.mean(a != b) * 100)
    return {"psnr": psnr, "mse": mse, "ssim": ssim, "changed_pct": changed}


def evaluate_embedding(
    cover: Image.Image,
    fractions=(0.05, 0.10, 0.25, 0.50, 0.75, 1.00),
    seed: int = 0,
) -> list[dict]:
    """
    Hide random data at several fill levels (percent of capacity) and measure
    quality (PSNR, MSE, SSIM) and detection (header check, RS analysis).
    """
    rng = np.random.default_rng(seed)
    capacity = max_payload_bytes(cover)
    rows = []
    for f in fractions:
        size = max(1, int(capacity * f))
        stego = encode_message(cover, rng.bytes(size))
        q = quality_metrics(cover, stego)
        rs_rate = rs_analysis(stego)["max_rate"]
        rows.append({
            "fill_pct": f * 100,
            "payload_bytes": size,
            "psnr": q["psnr"],
            "mse": q["mse"],
            "ssim": q["ssim"],
            "changed_pct": q["changed_pct"],
            "rs_rate_pct": rs_rate * 100,
            "rs_detected": bool(rs_rate >= RS_THRESHOLD),
            "header_detected": header_check(stego)["found"],
        })
    return rows


def clean_baseline(cover: Image.Image) -> dict:
    """Detection results on the untouched cover (should be 'not detected')."""
    rs_rate = rs_analysis(cover)["max_rate"]
    return {
        "rs_rate_pct": rs_rate * 100,
        "rs_detected": bool(rs_rate >= RS_THRESHOLD),
        "header_detected": header_check(cover)["found"],
    }