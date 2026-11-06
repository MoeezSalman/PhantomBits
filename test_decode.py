"""
Decode test: extract + decrypt a hidden message from a stego image.
Run:  python test_decode.py
"""

from modules.crypto import decrypt_message
from modules.steganography import extract_message
from utils.image_utils import load_image

# ---------- settings ----------
# Put the path of your encoded (stego) image here
STEGO_PATH = r"C:\Users\moeez\Downloads\phantom_stego.png"

# ---------- 1. Load stego image ----------
print("Loading stego image...")
stego = load_image(STEGO_PATH)
print(f"Image size: {stego.size}")

# ---------- 2. Extract hidden data ----------
print("Extracting hidden data...")
try:
    encrypted = extract_message(stego)
    print(f"Extracted encrypted payload: {len(encrypted)} bytes")
except Exception as e:
    print(f"❌ Extraction failed: {e}")
    exit(1)

# ---------- 3. Ask for password and decrypt ----------
password = input("Enter password: ").strip()

try:
    message = decrypt_message(encrypted, password)
    print("\n" + "="*50)
    print("✅ SUCCESS – Hidden message is:")
    print("="*50)
    print(message)
    print("="*50)
except ValueError as e:
    print(f"\n❌ Decryption failed: {e}")
    print("Wrong password or the image does not contain a valid message.")