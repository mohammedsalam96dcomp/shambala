import os
import io
import argparse
import struct

version_emerald = 'emerald'
version_firered = 'firered'

parser = argparse.ArgumentParser(description='Convert pokeemerald or pokefirered metatiles to use the triple layer system.' )
parser.add_argument('--tsroot', required=True,
                    help='Path to the tilesets directory in your pokeemerald/pokefirered project, e.g. /path/to/pokeemerald/data/tilesets')
parser.add_argument('--version', required=True, help = f'Game version: {version_emerald} or {version_firered}')

args = parser.parse_args()

if not os.path.exists(args.tsroot):
    print(f"Given tilesets root directory does not exist: {args.tsroot}")
    exit(1)

if args.version != version_emerald and args.version != version_firered:
    print(f"Game version '{args.version}' does not exist")
    exit(1)

if args.version == version_firered:
    layer_type_mask  = 0x60000000
    layer_type_shift = 29
    metatiles_size_factor = 4
    attribute_size = 4
    attribute_format = 'I'
else:
    layer_type_mask  = 0xF000
    layer_type_shift = 12
    metatiles_size_factor = 8
    attribute_size = 2
    attribute_format = 'H'

primary_path = os.path.join(args.tsroot, 'primary')
secondary_path = os.path.join(args.tsroot, 'secondary')

if not os.path.exists(primary_path):
    print(f"[ERR] Given tilesets root directory does not contain a primary folder, aborting.")
    exit(1)

if not os.path.exists(secondary_path):
    print(f"[ERR] Given tilesets root directory does not contain a secondary folder, aborting.")

tileset_dirs = []

_, dirs, _ = next(os.walk(primary_path))
tileset_dirs += map(lambda d: os.path.join(primary_path, d), dirs)
_, dirs, _ = next(os.walk(secondary_path))
tileset_dirs += map(lambda d: os.path.join(secondary_path, d), dirs)

for tileset_dir in tileset_dirs:
    tileset_name = os.path.basename(tileset_dir)
    metatiles_path = os.path.join(tileset_dir, 'metatiles.bin')
    metatile_attributes_path = os.path.join(tileset_dir, 'metatile_attributes.bin')
    if not os.path.exists(metatiles_path):
        print(f"[SKIP] {tileset_name} skipped because metatiles.bin was not found.")
        continue
    if not os.path.exists(metatile_attributes_path):
        print(f"[SKIP] {tileset_name} skipped because metatile_attributes.bin was not found.")
        continue
    if os.path.getsize(metatiles_path) != metatiles_size_factor*os.path.getsize(metatile_attributes_path):
        print(f"[SKIP] {tileset_name} skipped because metatiles.bin is not {metatiles_size_factor} times the size of metatile_attributes.bin (already converted?)")
        continue

    layer_types = []
    meta_attributes = []
    with open(metatile_attributes_path, 'rb') as fileobj:
        for chunk in iter(lambda: fileobj.read(attribute_size), ''):
            if chunk == b'':
                break
            metatile_attribute = struct.unpack(f'<{attribute_format}', chunk)[0]
            meta_attributes.append(metatile_attribute & ~layer_type_mask)
            layer_types.append((metatile_attribute & layer_type_mask) >> layer_type_shift)
    i = 0
    new_metatile_data = []
    with open(metatiles_path, 'rb') as fileobj:
        for chunk in iter(lambda: fileobj.read(16), ''):
            if chunk == b'':
                break
            metatile_data = struct.unpack('<HHHHHHHH', chunk)
            if layer_types[i] == 0:
                new_metatile_data += [0]*4
                new_metatile_data += metatile_data
            elif layer_types[i] == 1:
                new_metatile_data += metatile_data
                new_metatile_data += [0]*4
            elif layer_types[i] == 2:
                new_metatile_data += metatile_data[:4]
                new_metatile_data += [0]*4
                new_metatile_data += metatile_data[4:]
            else:
                new_metatile_data += [0]*12
            i += 1

    metatile_buffer = struct.pack(f'<{len(new_metatile_data)}H', *new_metatile_data)
    metatile_attribute_buffer = struct.pack(f'<{len(meta_attributes)}{attribute_format}', *meta_attributes)
    with open(metatiles_path, 'wb') as fileobj:
        fileobj.write(metatile_buffer)
    with open(metatile_attributes_path, 'wb') as fileobj:
        fileobj.write(metatile_attribute_buffer)
    print(f'[OK] Converted {tileset_name}')
