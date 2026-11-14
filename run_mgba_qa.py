#!/usr/bin/env python3
"""
Automated QA Tester for MLSS_EU_AR.gba in mGBA
With pauseOnFocusLost=0 configured, mGBA runs continuously.
"""

import os
import sys
import time
import subprocess
import ctypes
from ctypes import wintypes
from PIL import Image

ROM_PATH = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba"
MGBA_PATH = r"C:\Program Files\mGBA\mGBA.exe"
OUTPUT_DIR = r"C:\Users\user\Desktop\game\MLSS_AR\work\qa_screens"

os.makedirs(OUTPUT_DIR, exist_ok=True)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Virtual Key Codes
VK_RETURN = 0x0D   # Start
VK_KEY_X = 0x58    # Button A ('X')
VK_KEY_Z = 0x5A    # Button B ('Z')
VK_TAB = 0x09      # Fast-Forward toggle
VK_DOWN = 0x28
VK_UP = 0x26

def find_mgba_window():
    res = []
    def callback(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            if 'mGBA' in buff.value:
                res.append(hwnd)
        return True
    CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumWindows(CMPFUNC(callback), 0)
    return res[0] if res else None

def capture_screen(hwnd, filename):
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None

    hdc_screen = user32.GetDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    gdi32.SelectObject(hdc_mem, hbm)

    user32.PrintWindow(hwnd, hdc_mem, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG),
            ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
            ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
            ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
            ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
            ('biClrImportant', wintypes.DWORD)
        ]

    bih = BITMAPINFOHEADER()
    bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bih.biWidth = w
    bih.biHeight = -h
    bih.biPlanes = 1
    bih.biBitCount = 32

    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bih), 0)
    
    im = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
    filepath = os.path.join(OUTPUT_DIR, filename)
    im.save(filepath)

    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_screen)
    print(f"Captured: {filename} ({w}x{h})")
    return im

def send_key(hwnd, vk_code, hold=0.1, delay=0.5):
    user32.SetForegroundWindow(hwnd)
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(hold)
    user32.keybd_event(vk_code, 0, 2, 0)
    time.sleep(delay)

def main():
    print("=== STARTING MGBA QA RUNNER ===")
    proc = subprocess.Popen([MGBA_PATH, ROM_PATH])
    print("Waiting 12 seconds for GBA BIOS & game boot...")
    time.sleep(12)

    hwnd = find_mgba_window()
    if not hwnd:
        print("ERROR: mGBA window not found!")
        proc.terminate()
        return

    print(f"Found mGBA window hwnd: {hwnd}")
    user32.SetForegroundWindow(hwnd)
    time.sleep(1)

    # 1. Title Screen
    capture_screen(hwnd, "01_boot_title.png")

    # 2. Press START to enter Main Menu
    print("Pressing START...")
    send_key(hwnd, VK_RETURN, delay=2.5)
    capture_screen(hwnd, "02_main_menu.png")

    # 3. Select Mario & Luigi (Option 1) -> Press A ('X')
    print("Selecting Mario & Luigi (Button A)...")
    send_key(hwnd, VK_KEY_X, delay=2.5)
    capture_screen(hwnd, "03_lang_select.png")

    # 4. Confirm Language English (1st) -> Press A ('X')
    print("Confirming Language English (Button A)...")
    send_key(hwnd, VK_KEY_X, delay=2.5)
    capture_screen(hwnd, "04_file_select.png")

    # 5. File Select -> New Game -> Press A ('X')
    print("Starting New Game (Button A)...")
    send_key(hwnd, VK_KEY_X, delay=2.5)
    capture_screen(hwnd, "05_name_entry.png")

    # 6. Name Entry -> Press START to accept default name
    print("Accepting default name (START)...")
    send_key(hwnd, VK_RETURN, delay=3.0)
    capture_screen(hwnd, "06_intro_start.png")

    # 7. Fast forward through intro cutscene and capture dialogue frames
    print("Progressing into intro cutscene...")
    # Enable fast-forward toggle (Tab)
    send_key(hwnd, VK_TAB, delay=0.2)

    for i in range(1, 25):
        # Press A ('X') to advance dialogues
        send_key(hwnd, VK_KEY_X, hold=0.05, delay=0.4)
        if i % 2 == 0:
            capture_screen(hwnd, f"07_cutscene_{i:02d}.png")

    # Disable fast-forward
    send_key(hwnd, VK_TAB, delay=0.2)
    time.sleep(1)
    capture_screen(hwnd, "08_final_state.png")

    proc.terminate()
    print("\nQA run complete. Screenshots saved in:", OUTPUT_DIR)

if __name__ == '__main__':
    main()
