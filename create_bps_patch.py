#!/usr/bin/env python3
"""
Binary Patching System (BPS) generator and verifier for Mario & Luigi: Superstar Saga (EU) Arabic Translation.
Produces standard byuu BPS v1 compliant patch files compatible with Flips, Romhacking.net, and beat.
"""

import os
import sys
import zlib
import struct
import hashlib
import time

SRC_PATH = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba"
DST_PATH = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba"
PATCH_OUTPUT = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.bps"

def write_vli(val: int) -> bytes:
    out = bytearray()
    while True:
        x = val & 0x7F
        val >>= 7
        if val == 0:
            out.append(0x80 | x)
            break
        else:
            out.append(x)
            val -= 1
    return bytes(out)

def read_vli(stream: bytes, pos: int):
    data = 0
    shift = 1
    while True:
        b = stream[pos]
        pos += 1
        data += (b & 0x7F) * shift
        if b & 0x80:
            break
        shift <<= 7
        data += shift
    return data, pos

def create_bps_patch(source_bytes: bytes, target_bytes: bytes, metadata: bytes = b'') -> bytes:
    source_size = len(source_bytes)
    target_size = len(target_bytes)
    
    patch = bytearray(b'BPS1')
    patch.extend(write_vli(source_size))
    patch.extend(write_vli(target_size))
    patch.extend(write_vli(len(metadata)))
    if metadata:
        patch.extend(metadata)
        
    output_offset = 0
    target_offset = 0
    source_offset = 0
    
    # Process original ROM boundary
    while output_offset < source_size:
        if source_bytes[output_offset] == target_bytes[output_offset]:
            start = output_offset
            while output_offset < source_size and source_bytes[output_offset] == target_bytes[output_offset]:
                output_offset += 1
            length = output_offset - start
            patch.extend(write_vli(((length - 1) << 2) | 0))  # SourceRead
        else:
            start = output_offset
            while output_offset < source_size and source_bytes[output_offset] != target_bytes[output_offset]:
                output_offset += 1
            length = output_offset - start
            patch.extend(write_vli(((length - 1) << 2) | 1))  # TargetRead
            patch.extend(target_bytes[start:output_offset])
            
    # Process expanded area (0x01000000 onwards)
    last_nonzero = target_size - 1
    while last_nonzero >= output_offset and target_bytes[last_nonzero] == 0:
        last_nonzero -= 1
        
    if last_nonzero >= output_offset:
        data_len = (last_nonzero + 1) - output_offset
        patch.extend(write_vli(((data_len - 1) << 2) | 1))  # TargetRead
        patch.extend(target_bytes[output_offset : last_nonzero + 1])
        output_offset = last_nonzero + 1
        
    # Compress trailing zero-padding using RLE TargetCopy
    if output_offset < target_size:
        # Write first 0x00
        patch.extend(write_vli(((1 - 1) << 2) | 1))
        patch.append(0x00)
        zero_pos = output_offset
        output_offset += 1
        
        remaining = target_size - output_offset
        if remaining > 0:
            rel = zero_pos - target_offset
            enc_rel = ((-rel) << 1) | 1 if rel < 0 else (rel << 1)
            patch.extend(write_vli(((remaining - 1) << 2) | 3))  # TargetCopy
            patch.extend(write_vli(enc_rel))
            target_offset = zero_pos + remaining
            output_offset += remaining
            
    # Trailer
    source_crc = zlib.crc32(source_bytes) & 0xFFFFFFFF
    target_crc = zlib.crc32(target_bytes) & 0xFFFFFFFF
    patch.extend(struct.pack('<II', source_crc, target_crc))
    patch_crc = zlib.crc32(patch) & 0xFFFFFFFF
    patch.extend(struct.pack('<I', patch_crc))
    return bytes(patch)

def apply_bps_patch(source_bytes: bytes, patch_bytes: bytes) -> bytes:
    if patch_bytes[:4] != b'BPS1':
        raise ValueError("Invalid BPS header magic!")
    pos = 4
    source_size, pos = read_vli(patch_bytes, pos)
    target_size, pos = read_vli(patch_bytes, pos)
    meta_len, pos = read_vli(patch_bytes, pos)
    metadata = patch_bytes[pos:pos+meta_len]
    pos += meta_len
    
    if len(source_bytes) != source_size:
        raise ValueError(f"Source size mismatch: expected {source_size}, got {len(source_bytes)}")
        
    output = bytearray(target_size)
    output_offset = 0
    source_offset = 0
    target_offset = 0
    
    patch_data_end = len(patch_bytes) - 12
    while pos < patch_data_end:
        val, pos = read_vli(patch_bytes, pos)
        action = val & 3
        length = (val >> 2) + 1
        
        if action == 0:  # SourceRead
            output[output_offset : output_offset + length] = source_bytes[output_offset : output_offset + length]
            output_offset += length
        elif action == 1:  # TargetRead
            output[output_offset : output_offset + length] = patch_bytes[pos : pos + length]
            pos += length
            output_offset += length
        elif action == 2:  # SourceCopy
            offset_val, pos = read_vli(patch_bytes, pos)
            rel = (offset_val >> 1) * (-1 if (offset_val & 1) else 1)
            source_offset += rel
            for _ in range(length):
                output[output_offset] = source_bytes[source_offset]
                output_offset += 1
                source_offset += 1
        elif action == 3:  # TargetCopy
            offset_val, pos = read_vli(patch_bytes, pos)
            rel = (offset_val >> 1) * (-1 if (offset_val & 1) else 1)
            target_offset += rel
            for _ in range(length):
                output[output_offset] = output[target_offset]
                output_offset += 1
                target_offset += 1
                
    source_crc, target_crc, patch_crc = struct.unpack('<III', patch_bytes[-12:])
    computed_src_crc = zlib.crc32(source_bytes) & 0xFFFFFFFF
    computed_tgt_crc = zlib.crc32(output) & 0xFFFFFFFF
    computed_patch_crc = zlib.crc32(patch_bytes[:-4]) & 0xFFFFFFFF
    
    if computed_src_crc != source_crc:
        raise ValueError(f"Source CRC mismatch: 0x{computed_src_crc:08X} vs 0x{source_crc:08X}")
    if computed_tgt_crc != target_crc:
        raise ValueError(f"Target CRC mismatch: 0x{computed_tgt_crc:08X} vs 0x{target_crc:08X}")
    if computed_patch_crc != patch_crc:
        raise ValueError(f"Patch CRC mismatch: 0x{computed_patch_crc:08X} vs 0x{patch_crc:08X}")
        
    return bytes(output)

def main():
    print("=" * 60)
    print("Mario & Luigi: Superstar Saga (EU) - BPS Patch Generator")
    print("=" * 60)
    
    if not os.path.exists(SRC_PATH):
        print(f"Error: Source ROM not found at {SRC_PATH}")
        sys.exit(1)
    if not os.path.exists(DST_PATH):
        print(f"Error: Target ROM not found at {DST_PATH}")
        sys.exit(1)
        
    print(f"Reading source: {SRC_PATH}")
    with open(SRC_PATH, 'rb') as f:
        src = f.read()
    print(f"  Size: {len(src):,} bytes | CRC32: {zlib.crc32(src)&0xFFFFFFFF:08X} | SHA1: {hashlib.sha1(src).hexdigest()}")
    
    print(f"Reading target: {DST_PATH}")
    with open(DST_PATH, 'rb') as f:
        dst = f.read()
    print(f"  Size: {len(dst):,} bytes | CRC32: {zlib.crc32(dst)&0xFFFFFFFF:08X} | SHA1: {hashlib.sha1(dst).hexdigest()}")
    
    metadata = b"Mario & Luigi: Superstar Saga (EU) - Arabic Translation v1.0 by Antigravity"
    print("\nGenerating BPS patch...")
    t0 = time.time()
    patch = create_bps_patch(src, dst, metadata)
    t1 = time.time()
    print(f"  Patch generated in {t1 - t0:.2f}s | Size: {len(patch):,} bytes")
    
    # Write to primary target
    with open(PATCH_OUTPUT, 'wb') as f:
        f.write(patch)
    print(f"  Saved patch to: {PATCH_OUTPUT}")
    
    # Also write a copy to the root game directory
    alt_output = r"C:\Users\user\Desktop\game\MLSS_EU_AR.bps"
    with open(alt_output, 'wb') as f:
        f.write(patch)
    print(f"  Saved copy to: {alt_output}")
    
    print("\nVerifying patch application integrity...")
    reconstructed = apply_bps_patch(src, patch)
    if reconstructed == dst:
        print("  VERIFICATION SUCCESS: Reconstructed ROM matches Target ROM 100% bit-for-bit!")
    else:
        print("  VERIFICATION FAILED: Reconstructed ROM differs from target!")
        sys.exit(1)
        
    patch_crc = zlib.crc32(patch[:-4]) & 0xFFFFFFFF
    print(f"\nFinal Patch Details:")
    print(f"  Source CRC32: {zlib.crc32(src)&0xFFFFFFFF:08X}")
    print(f"  Target CRC32: {zlib.crc32(dst)&0xFFFFFFFF:08X}")
    print(f"  Patch CRC32:  {patch_crc:08X}")
    print(f"  Patch SHA1:   {hashlib.sha1(patch).hexdigest()}")
    print("=" * 60)

if __name__ == '__main__':
    main()
