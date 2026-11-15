"""Tests for steganalysis (header check, RS analysis) and evaluation."""

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from modules.steganography import encode_message
from modules.steganalysis import header_check, rs_analysis
from modules.evaluation import quality_metrics, evaluate_embedding, clean_baseline
from utils.image_utils import max_payload_bytes


def make_image(h=200, w=300, seed=1) -> Image.Image:
    """Smooth, photo-like synthetic image."""
    rng = np.random.default_rng(seed)
    a = gaussian_filter(rng.normal(128, 60, (h, w, 3)), (3, 3, 0))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def test_header_check_clean_image():
    result = header_check(make_image())
    assert result["found"] is False
    assert result["length"] is None


def test_header_check_finds_short_message():
    stego = encode_message(make_image(), b"x" * 60)
    result = header_check(stego)
    assert result["found"] is True
    assert result["length"] == 60


def test_rs_clean_image_is_low():
    assert rs_analysis(make_image())["max_rate"] < 0.30


def test_rs_detects_large_message():
    img = make_image()
    data = np.random.default_rng(0).bytes(max_payload_bytes(img) // 2)
    assert rs_analysis(encode_message(img, data))["max_rate"] >= 0.30


def test_quality_identical_images():
    img = make_image()
    q = quality_metrics(img, img)
    assert q["mse"] == 0
    assert q["psnr"] == 99.0
    assert q["changed_pct"] == 0


def test_quality_stego_is_still_good():
    img = make_image()
    stego = encode_message(img, b"hello world" * 50)
    q = quality_metrics(img, stego)
    assert q["psnr"] > 40
    assert q["ssim"] > 0.95


def test_evaluate_embedding_rows():
    rows = evaluate_embedding(make_image(), fractions=(0.1, 0.5, 1.0))
    assert len(rows) == 3
    assert all(r["header_detected"] for r in rows)
    # more data -> lower PSNR
    assert rows[0]["psnr"] > rows[-1]["psnr"]


def test_clean_baseline_not_detected():
    base = clean_baseline(make_image())
    assert base["header_detected"] is False
    assert base["rs_detected"] is False
    