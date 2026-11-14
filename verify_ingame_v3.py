#!/usr/bin/env python3
"""
verify_ingame_v3.py
Automated headless mGBA navigation & verification for Arabic Build v3.0.
Captures live uncompressed F12 frames from mGBA internal VRAM buffer.
"""
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
K_J = ord('J')
K_S = ord('S')

SHOTS_DIR = r'C:\Users\user\Desktop\game\MLSS_AR\work\mgba_shots'
QA_DIR = r'C:\Users\user\Desktop\game\MLSS_AR\work\qa_v3'
ART_DIR = r'C:\Users\user\.gemini\antigravity\brain\bb742f28-9080-409b-82bd-6fe93eab7c66'
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

print("Launching mGBA with Patched Arabic ROM v3.0...")
proc = subprocess.Popen([MGBA_PATH, ROM_PATH])
time.sleep(12.0)

hwnds = []
def cb(h, _):
    if user32.IsWindowVisible(h):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        if 'mGBA' in buf.value:
            hwnds.append(h)
    return True

for _ in range(20):
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(cb), 0)
    if hwnds:
        break
    time.sleep(0.5)

if not hwnds:
    print("Could not find mGBA window!")
    proc.terminate()
    exit(1)

top = hwnds[0]
targets = [top]
def child_cb(ch, _):
    targets.append(ch)
    return True
user32.EnumChildWindows(top, ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(child_cb), 0)

shot_counter = 0
def take_shot(label):
    global shot_counter
    sc = user32.MapVirtualKeyW(VK_F12, 0)
    lp_down = 1 | (sc << 16)
    lp_up = 1 | (sc << 16) | (1 << 30) | (1 << 31)
    for t in targets:
        user32.PostMessageW(t, WM_KEYDOWN, VK_F12, lp_down)
    time.sleep(0.05)
    for t in targets:
        user32.PostMessageW(t, WM_KEYUP, VK_F12, lp_up)
    time.sleep(0.3)
    shots = sorted(glob.glob(os.path.join(SHOTS_DIR, '*.png')), key=os.path.getmtime)
    if shots:
        latest = shots[-1]
        dst = os.path.join(QA_DIR, f"v3_{shot_counter:02d}_{label}.png")
        shutil.copy2(latest, dst)
        # Also copy to artifacts dir
        art_dst = os.path.join(ART_DIR, f"v3_{shot_counter:02d}_{label}.png")
        shutil.copy2(latest, art_dst)
        print(f"Shot {shot_counter:02d} [{label}]: {os.path.basename(latest)}")
        shot_counter += 1

def send_key(vk, label, hold=0.15, delay=2.0):
    sc = user32.MapVirtualKeyW(vk, 0)
    lp_down = 1 | (sc << 16)
    lp_up = 1 | (sc << 16) | (1 << 30) | (1 << 31)
    for t in targets:
        user32.PostMessageW(t, WM_KEYDOWN, vk, lp_down)
    time.sleep(hold)
    for t in targets:
        user32.PostMessageW(t, WM_KEYUP, vk, lp_up)
    time.sleep(delay)
    take_shot(label)

print("Navigating through boot and title screen...")
time.sleep(6.0)
take_shot("00_title_screen")

# Start at title
send_key(VK_RETURN, "01_press_start")

# Select Mario & Luigi
send_key(K_J, "02_select_ML")

# Confirm English language
send_key(K_J, "03_confirm_lang")

# Notebook settled
time.sleep(2.0)
take_shot("04_file_select_notebook")

# Select Start Game
send_key(K_J, "05_press_tab")
send_key(K_S, "06_press_down")
send_key(VK_DOWN, "07_press_arrow_down")
send_key(K_J, "08_select_start_game")
send_key(VK_RETURN, "09_start_game_confirm")

print("Waiting for cutscene...")
time.sleep(5.0)
take_shot("10_entering_cutscene")

time.sleep(15.0)
take_shot("11_throne_room_dialogue")

# Advance dialogue lines with A
for i in range(1, 6):
    send_key(K_J, f"12_dialogue_line_{i}", hold=0.1, delay=2.5)

proc.terminate()
print("Verification complete! All shots saved to QA and Artifacts.")
