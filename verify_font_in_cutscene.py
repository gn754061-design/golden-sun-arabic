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
VK_RETURN = 0x0D   # Start
VK_KEY_X = 0x58    # Button A ('X')
VK_KEY_Z = 0x5A    # Button B ('Z')
VK_TAB = 0x09      # Fast-Forward toggle
VK_F12 = 0x7B

SHOTS_DIR = "./work/"mgba_shots'
QA_DIR = "./work/"qa_verified_final_font'
ROM_PATH = "./work/"MLSS_EU_AR.gba'
MGBA_PATH = r'C:\Program Files\mGBA\mGBA.exe'

os.makedirs(SHOTS_DIR, exist_ok=True)
os.makedirs(QA_DIR, exist_ok=True)
for p in glob.glob(os.path.join(SHOTS_DIR, '*.png')):
    try: os.remove(p)
    except: pass
for p in glob.glob(os.path.join(QA_DIR, '*.png')):
    try: os.remove(p)
    except: pass

print("Launching mGBA...")
proc = subprocess.Popen([MGBA_PATH, ROM_PATH])
print("Waiting 12s for GBA BIOS boot...")
time.sleep(12.0)

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
time.sleep(1.0)

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

# 1. Title Screen
print("[1] Title screen...")
take_f12()

# 2. Press START to enter Main Menu
print("[2] Pressing START...")
send_key(VK_RETURN, delay=2.5)
take_f12()

# 3. Select Mario & Luigi -> Press A ('X')
print("[3] Selecting Mario & Luigi (A)...")
send_key(VK_KEY_X, delay=2.5)
take_f12()

# 4. Confirm Language English -> Press A ('X')
print("[4] Confirming Language English (A)...")
send_key(VK_KEY_X, delay=2.5)
take_f12()

# 5. File Select -> New Game -> Press A ('X')
print("[5] Starting New Game (A)...")
send_key(VK_KEY_X, delay=2.5)
take_f12()

# 6. Name Entry -> Press START to accept default name
print("[6] Accepting default name (START)...")
send_key(VK_RETURN, delay=3.5)
take_f12()

# 7. Progressing into intro cutscene
print("[7] Progressing into intro cutscene with Fast-Forward...")
send_key(VK_TAB, delay=0.2)

for i in range(1, 30):
    send_key(VK_KEY_X, hold=0.05, delay=0.3)
    if i >= 8:
        take_f12()

# Disable fast-forward
send_key(VK_TAB, delay=0.2)
time.sleep(1.0)

for i in range(5):
    take_f12()
    time.sleep(0.5)

proc.terminate()

shots = sorted(glob.glob(os.path.join(SHOTS_DIR, '*.png')), key=os.path.getmtime)
print(f"\nCaptured {len(shots)} frames total in {SHOTS_DIR}:")
for idx, s in enumerate(shots):
    dst = os.path.join(QA_DIR, f"final_frame_{idx:02d}.png")
    shutil.copy2(s, dst)
    print(f"  [{idx:02d}] {os.path.basename(s)} -> final_frame_{idx:02d}.png ({os.path.getsize(s):,} bytes)")

print("\nVerification Capture Finished!")
