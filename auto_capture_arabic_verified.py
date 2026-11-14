import ctypes
import subprocess
import time
import glob
import os
import shutil

user32 = ctypes.windll.user32
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_F12 = 0x7B
VK_RETURN = 0x0D
VK_DOWN = 0x28
K_A = ord('J')
K_S = ord('S')
K_X = ord('X')

SHOTS_DIR = r'C:\Users\user\Desktop\game\MLSS_AR\work\mgba_shots'
QA_DIR = r'C:\Users\user\Desktop\game\MLSS_AR\work\qa_verified_new_font'
ROM_PATH = r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba'
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
all_targets = [top]
def child_cb(ch, _):
    all_targets.append(ch)
    return True
user32.EnumChildWindows(top, ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(child_cb), 0)
print(f"Target HWNDs: {all_targets}")

def post_key(vk, hold=0.15, delay=1.0):
    sc = user32.MapVirtualKeyW(vk, 0)
    lp_down = 1 | (sc << 16)
    lp_up = 1 | (sc << 16) | (1 << 30) | (1 << 31)
    for t in all_targets:
        user32.PostMessageW(t, WM_KEYDOWN, vk, lp_down)
    time.sleep(hold)
    for t in all_targets:
        user32.PostMessageW(t, WM_KEYUP, vk, lp_up)
    time.sleep(delay)

def take_shot():
    sc = user32.MapVirtualKeyW(VK_F12, 0)
    lp_down = 1 | (sc << 16)
    lp_up = 1 | (sc << 16) | (1 << 30) | (1 << 31)
    for t in all_targets:
        user32.PostMessageW(t, WM_KEYDOWN, VK_F12, lp_down)
    time.sleep(0.05)
    for t in all_targets:
        user32.PostMessageW(t, WM_KEYUP, VK_F12, lp_up)
    time.sleep(0.2)

print("[1] Waiting 12s for title screen...")
time.sleep(12.0)
take_shot()

print("[2] Pressing Start to open mode select...")
post_key(VK_RETURN, delay=2.5)
take_shot()

print("[3] Selecting Mario & Luigi (Option 1) with Button A...")
post_key(K_A, delay=0.1)
post_key(K_X, delay=2.5)
take_shot()

print("[4] Confirming English (Option 1) with Button A...")
post_key(K_A, delay=0.1)
post_key(K_X, delay=3.0)
take_shot()

print("[5] Moving down from tab to 'Start Game'...")
post_key(K_S, delay=0.1)
post_key(VK_DOWN, delay=1.5)
take_shot()

print("[6] Confirming 'Start Game' with Button A...")
post_key(K_A, delay=0.1)
post_key(K_X, delay=0.1)
post_key(VK_RETURN, delay=3.0)
take_shot()

print("[7] Confirming Name 'MARIO' with Start...")
post_key(VK_RETURN, delay=3.5)
take_shot()

print("[8] Cutscene starting! Waiting 23s for Throne Room speech...")
time.sleep(23.0)

print("[9] Capturing Dialogue sequence (20 frames)...")
for i in range(20):
    take_shot()
    time.sleep(0.6)

proc.terminate()

shots = sorted(glob.glob(os.path.join(SHOTS_DIR, '*.png')), key=os.path.getmtime)
print(f"\nCaptured {len(shots)} frames total in {SHOTS_DIR}:")
for idx, s in enumerate(shots):
    dst = os.path.join(QA_DIR, f"frame_{idx:02d}.png")
    shutil.copy2(s, dst)
    print(f"  [{idx:02d}] {os.path.basename(s)} -> frame_{idx:02d}.png ({os.path.getsize(s):,} bytes)")

print("\nVerification Capture Finished!")
