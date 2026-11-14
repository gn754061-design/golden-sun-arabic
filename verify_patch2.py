import zlib
import struct

with open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.bps', 'rb') as f:
    patch = f.read()

print('Patch size:', len(patch))
print('Header:', patch[:4])

source_crc = int.from_bytes(patch[-12:-8], 'big')
target_crc = int.from_bytes(patch[-8:-4], 'big')
patch_crc = int.from_bytes(patch[-4:], 'big')

print('Source CRC in patch:', hex(source_crc))
print('Target CRC in patch:', hex(target_crc))
print('Patch CRC:', hex(patch_crc))

with open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba', 'rb') as f:
    source = f.read()
with open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba', 'rb') as f:
    target = f.read()

print('Actual source CRC:', hex(zlib.crc32(source) & 0xFFFFFFFF))
print('Actual target CRC:', hex(zlib.crc32(target) & 0xFFFFFFFF))
print('Patch CRC of patch data:', hex(zlib.crc32(patch[:-4]) & 0xFFFFFFFF))

# Try to apply the simple patch
# The patch format is: BPS1 + target_len(varint) + 0 + target_data + source_crc + target_crc + patch_crc
patch_data = open(r'C:\Users\user\Desktop\game\MLSS_EU_AR.bps', 'rb').read()
target_len = len(open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba', 'rb').read())
print('Target length:', target_len)
print('Patch length:', len(patch))
print('Target data in patch length:', len(patch) - 4 - 12 - 1)  # BPS1 + varint + 0 + 12 bytes CRCs + 4 patch CRC