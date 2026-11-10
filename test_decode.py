"""
Decode test: extract + decrypt a hidden message from a stego image.

Usage:
  py test_decode.py
  py test_decode.py path/to/stego.png
  py test_decode.py "C:/Users/.../file.png"
"""

from modules.crypto import decrypt_message
from modules.steganography import extract_message
from utils.image_utils import load_image
import sys
from pathlib import Path

# ---------- settings ----------
# Usage:
#   py test_decode.py                          → looks for "phantom_stego.png" in current folder
#   py test_decode.py path/to/stego.png        → uses the given path
#   py test_decode.py "C:/Users/.../file.png"  → also works with full Windows path
if len(sys.argv) > 1:
    STEGO_PATH = sys.argv[1]
else:
    STEGO_PATH = "phantom_stego.png"          # default: same folder as the script

print(f"Using stego image: {STEGO_PATH}")

# ---------- 1. Load stego image ----------
print("Loading stego image...")
try:
    stego = load_image(STEGO_PATH)
    print(f"Image size: {stego.size}")
except Exception as e:
    print(f"❌ Cannot load image: {e}")
    sys.exit(1)

# ---------- 2. Extract hidden data ----------
print("Extracting hidden data...")
try:
    encrypted = extract_message(stego)
    print(f"Extracted encrypted payload: {len(encrypted)} bytes")
except Exception as e:
    print(f"❌ Extraction failed: {e}")
    sys.exit(1)

# ---------- 3. Ask for password and decrypt ----------
password = input("\nEnter password: ").strip()
if not password:
    print("❌ Password cannot be empty")
    sys.exit(1)

try:
    message = decrypt_message(encrypted, password)
    print("\n✅ SUCCESS – Hidden message is:")
    print("'" + message + "'\n")
except ValueError as e:
    print(f"\n❌ {e}\n")