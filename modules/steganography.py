"""
LSB steganography – hide / extract arbitrary bytes inside RGB PNG images.
"""

from __future__ import annotations
from typing import Tuple
import numpy as np
from PIL import Image

from utils.image_utils import (
    load_image,
    image_to_array,
    array_to_image,
    max_payload_bytes,
)


def _bytes_to_bits(data: bytes) -> np.ndarray:
    """Convert bytes → 1-D array of bits (0/1)."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    """Convert 1-D bit array → bytes (pad to multiple of 8)."""
    # pad if necessary
    pad = (8 - len(bits) % 8) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    return np.packbits(bits).tobytes()


def encode_message(image: Image.Image, data: bytes) -> Image.Image:
    """
    Embed `data` into the LSBs of the image.

    A 32-bit big-endian length header is written first so the
    extractor knows exactly how many bits to read.
    """
    if not data:
        raise ValueError("No data to embed")

    max_bytes = max_payload_bytes(image)
    if len(data) > max_bytes:
        raise ValueError(
            f"Message too large for this image. "
            f"Max capacity = {max_bytes} bytes, got {len(data)} bytes."
        )

    # 32-bit length header + payload
    length_header = len(data).to_bytes(4, byteorder="big")
    full_payload = length_header + data
    bits = _bytes_to_bits(full_payload)

    arr = image_to_array(image).copy()          # (H, W, 3)
    flat = arr.reshape(-1)                      # all colour channels flattened

    if len(bits) > len(flat):
        raise ValueError("Internal error: not enough pixels")

    # Clear the LSB and set the new bit
    flat[: len(bits)] = (flat[: len(bits)] & 0xFE) | bits

    encoded = flat.reshape(arr.shape)
    return array_to_image(encoded)


def extract_message(image: Image.Image) -> bytes:
    """
    Extract the hidden bytes that were previously embedded by encode_message.
    """
    arr = image_to_array(image)
    flat = arr.reshape(-1)

    # First 32 bits = length of the payload (in bytes)
    length_bits = flat[:32] & 1
    length_bytes = _bits_to_bytes(length_bits)
    payload_len = int.from_bytes(length_bytes, byteorder="big")

    if payload_len <= 0 or payload_len > max_payload_bytes(image):
        raise ValueError("No valid hidden message found (bad length header)")

    # Next payload_len * 8 bits are the actual data
    total_bits_needed = 32 + payload_len * 8
    if total_bits_needed > len(flat):
        raise ValueError("Image does not contain enough data")

    data_bits = flat[32:total_bits_needed] & 1
    return _bits_to_bytes(data_bits)[:payload_len]