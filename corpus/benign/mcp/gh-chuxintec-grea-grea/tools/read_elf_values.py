#!/usr/bin/env python3
"""Read typed constants from file-backed ELF virtual addresses (read-only)."""
import argparse
import json
import struct
from grea.host.paths import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog='Addresses must be link-time ELF virtual addresses. Subtract any analysis-tool rebase or runtime load bias explicitly. No code is executed.')
    parser.add_argument('elf', type=Path)
    parser.add_argument('--address', type=lambda x: int(x, 0), action='append', required=True)
    parser.add_argument('--type', choices=['f32', 'f64', 'u32', 'i32', 'u64', 'i64'], default='f32')
    parser.add_argument('--count', type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.count <= 1024:
        parser.error('--count must be 1..1024')
    try:
        data = args.elf.read_bytes()
        if data[:4] != b'\x7fELF' or data[4] not in (1, 2) or data[5] not in (1, 2):
            raise ValueError('Unsupported or invalid ELF identification')
        endian = '<' if data[5] == 1 else '>'
        is64 = data[4] == 2
        offset = struct.unpack_from(endian + ('Q' if is64 else 'I'), data, 32 if is64 else 28)[0]
        size, count = struct.unpack_from(endian + 'HH', data, 54 if is64 else 42)
        expected = 56 if is64 else 32
        if size < expected or count == 0xffff or offset + size * count > len(data):
            raise ValueError('Invalid or unsupported program header table')
        segments = []
        for index in range(count):
            row = struct.unpack_from(endian + ('IIQQQQQQ' if is64 else 'IIIIIIII'), data, offset + index * size)
            kind, file_offset, virtual, length = (row[0], row[2], row[3], row[5]) if is64 else (row[0], row[1], row[2], row[4])
            if kind == 1:
                segments.append((file_offset, virtual, length))
        code = {'f32': 'f', 'f64': 'd', 'u32': 'I', 'i32': 'i', 'u64': 'Q', 'i64': 'q'}[args.type]
        fmt = endian + code * args.count
        length = struct.calcsize(fmt)
        output = []
        for address in args.address:
            matches = [(o + address - v) for o, v, n in segments if v <= address and address + length <= v + n]
            if len(matches) != 1 or matches[0] + length > len(data):
                raise ValueError(f'{address:#x}: no unique file-backed mapping for entire value range')
            values = struct.unpack_from(fmt, data, matches[0])
            output.append({'address': hex(address), 'fileOffset': matches[0], 'type': args.type, 'values': values})
        print(json.dumps(output, allow_nan=False))
    except (OSError, ValueError, IndexError, struct.error) as error:
        parser.error(str(error))

if __name__ == '__main__':
    main()
