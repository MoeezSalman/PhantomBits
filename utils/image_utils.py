"""
Image utility helpers used by steganography and evaluation.
"""

from __future__ import annotations
from typing import Tuple
import numpy as np
from PIL import Image


def load_image(path_or_file) -> Image.Image:
    """Load an image and force RGB mode (drop alpha if present)."""
    img = Image.open(path_or_file)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def image_to_array(img: Image.Image) -> np.ndarray:
    """Convert PIL Image → uint8 NumPy array of shape (H, W, 3)."""
    return np.array(img, dtype=np.uint8)


def array_to_image(arr: np.ndarray) -> Image.Image:
    """Convert uint8 NumPy array → PIL Image."""
    return Image.fromarray(arr.astype(np.uint8), mode="RGB")


def max_payload_bytes(img: Image.Image) -> int:
    """
    Maximum number of *bytes* we can hide.

    We use 1 LSB per colour channel → 3 bits per pixel.
    We reserve the first 32 bits for a length header.
    """
    w, h = img.size
    total_bits = w * h * 3
    usable_bits = total_bits - 32          # 32-bit length header
    return usable_bits // 8


def calculate_psnr(original: Image.Image, encoded: Image.Image) -> float:
    """Simple Peak-Signal-to-Noise-Ratio between two RGB images."""
    from skimage.metrics import peak_signal_noise_ratio
    orig = image_to_array(original)
    enc  = image_to_array(encoded)
    return float(peak_signal_noise_ratio(orig, enc, data_range=255))