#!/usr/bin/env python3
"""
verify_title_and_menu.py
Captures live, pixel-perfect frames of:
1. Title screen with 100% Arabic 'اضغط ابدأ'
2. Notebook file select screen with centered 'لعبة جديدة' and clean inactive tabs
3. In-game dialogues in cutscenes
"""

import ctypes
import subprocess
import time
import glob
import os
import shutil
from PIL import Image

user32 = ctypes.windll.user32
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_F12 = 0x7B
VK_RETURN = 0x0D   # Start
VK_KEY_X = 0x58    # Button A ('X')
VK_KEY_Z = 0x5A    # Button B ('Z')
VK_TAB = 0x09      # Fast-Forward toggle

SHOTS_DIR = r'C:\Users\user\Desktop\game\MLSS_AR\work\mgba_shots'
OUTPUT_DIR = r'C:\Users\user\Desktop\game\MLSS_AR\work\final_verified_v3'
ART_DIR = r'C:\Users\user\.gemini\antigravity\brain\bb742f28-9080-409b-82bd-6fe93eab7c66'

os.makedirs(SHOTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
for p in glob.glob(os.path.join(SHOTS_DIR, '*.png')):
    try: os.remove(p)
    except: pass

ROM_PATH = r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba'
MGBA_PATH = r'C:\Program Files\mGBA\mGBA.exe'

print("Launching mGBA with Patched Arabic ROM v3.0...")
proc = subprocess.Popen([MGBA_PATH, ROM_PATH])
time.sleep(8.0)

hwnds = []
def cb(h, _):
    if user32.IsWindowVisible(h):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        if 'mGBA' in buf.value: hwnds.append(h)
    return True

for _ in range(20):
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
    if hwnds: break
    time.sleep(0.5)

top = hwnds[0]
user32.SetForegroundWindow(top)

def send_key(vk_code, hold=0.1, delay=0.5):
    user32.SetForegroundWindow(top)
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(hold)
    user32.keybd_event(vk_code, 0, 2, 0)
    time.sleep(delay)

def take_f12():
    sc = user32.MapVirtualKeyW(VK_F12, 0)
    lp_down = 1 | (sc << 16)
    lp_up = 1 | (sc << 16) | (1 << 30) | (1 << 31)
    user32.PostMessageW(top, WM_KEYDOWN, VK_F12, lp_down)
    time.sleep(0.05)
    user32.PostMessageW(top, WM_KEYUP, VK_F12, lp_up)
    time.sleep(0.2)

# Step 1: Wait for Title Screen animation and capture title screen loop
print("[1] Capturing Title Screen ('اضغط ابدأ')...")
for i in range(8):
    take_f12()
    time.sleep(0.6)

# Step 2: Press START to enter Main Menu
print("[2] Pressing START...")
send_key(VK_RETURN, delay=2.0)
take_f12()

# Step 3: Select Mario & Luigi (A)
print("[3] Selecting Mario & Luigi...")
send_key(VK_KEY_X, delay=2.0)
take_f12()

# Step 4: Confirm Language (A)
print("[4] Confirming Language...")
send_key(VK_KEY_X, delay=2.5)
take_f12()

# Step 5: Notebook File Select
print("[5] Capturing Notebook File Select Screen...")
take_f12()
time.sleep(0.5)
take_f12()

# Step 6: Start Game (A)
print("[6] Starting New Game...")
send_key(VK_KEY_X, delay=2.0)
take_f12()

# Step 7: Confirm Default Name (START)
print("[7] Accepting Default Name...")
send_key(VK_RETURN, delay=3.0)
take_f12()

# Step 8: Progress into Cutscene with fast-forward
print("[8] Progressing into cutscene with fast-forward...")
send_key(VK_TAB, delay=0.2)
for i in range(25):
    send_key(VK_KEY_X, hold=0.05, delay=0.3)
    if i >= 6:
        take_f12()

send_key(VK_TAB, delay=0.2)
time.sleep(1.0)
for _ in range(5):
    take_f12()
    time.sleep(0.4)

proc.terminate()

shots = sorted(glob.glob(os.path.join(SHOTS_DIR, '*.png')), key=os.path.getmtime)
print(f"\nCaptured {len(shots)} frames total.")

for idx, s in enumerate(shots):
    dst = os.path.join(OUTPUT_DIR, f"shot_{idx:02d}.png")
    shutil.copy2(s, dst)

print("Verification complete! Checkshots saved to final_verified_v3.")
