#!/usr/bin/env python3
import struct
import math
import sys
import os
import time
import lzma
import tempfile
from collections import Counter

# Magic header for our LZMA-based compressor
MAGIC = b'LZHC'

# Varint encoding/decoding functions
def write_varint(n: int) -> bytes:
    out = bytearray()
    while True:
        to_write = n & 0x7F
        n >>= 7
        if n:
            out.append(to_write | 0x80)
        else:
            out.append(to_write)
            break
    return bytes(out)

def read_varint(stream) -> int:
    shift = 0
    result = 0
    while True:
        b = stream.read(1)
        if not b:
            raise EOFError("Unexpected EOF in varint stream")
        byte = b[0]
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result

# Zigzag functions
def zigzag_encode(n: int) -> int:
    return (n << 1) ^ (n >> 31)

def zigzag_decode(z: int) -> int:
    return (z >> 1) ^ -(z & 1)

# Compressor using LZMA on varint-coded deltas
def compress_file(infile: str, outfile: str) -> None:
    vals = []
    breaks = []
    idx = 0
    with open(infile, 'r') as f:
        for line in f:
            nums = [int(x) for x in line.split()]
            vals.extend(nums)
            idx += len(nums)
            breaks.append(idx)
    if not vals:
        raise ValueError("Empty input file")

    d1 = [vals[i] - vals[i-1] for i in range(1, len(vals))]
    d2 = [d1[0]] + [d1[i] - d1[i-1] for i in range(1, len(d1))]
    zs = [zigzag_encode(d) for d in d2]

    raw = bytearray()
    for z in zs:
        raw.extend(write_varint(z))

    comp = lzma.compress(bytes(raw), preset=9)

    with open(outfile, 'wb') as out:
        out.write(MAGIC)
        out.write(struct.pack('<I', len(vals)))
        out.write(struct.pack('<i', vals[0]))
        out.write(struct.pack('<I', len(breaks)))
        for b in breaks:
            out.write(struct.pack('<I', b))
        out.write(comp)


def decompress_file(infile: str, outfile: str) -> None:
    with open(infile, 'rb') as inp:
        if inp.read(4) != MAGIC:
            raise ValueError("Not an LZHC file")
        n = struct.unpack('<I', inp.read(4))[0]
        h0 = struct.unpack('<i', inp.read(4))[0]
        nb = struct.unpack('<I', inp.read(4))[0]
        breaks = [struct.unpack('<I', inp.read(4))[0] for _ in range(nb)]
        comp = inp.read()

    raw = lzma.decompress(comp)
    from io import BytesIO
    stream = BytesIO(raw)

    zs = []
    while len(zs) < n-1:
        zs.append(read_varint(stream))

    d2 = [zigzag_decode(z) for z in zs]
    d1 = [d2[0]]
    for i in range(1, len(d2)):
        d1.append(d2[i] + d1[i-1])
    vals = [h0]
    for d in d1:
        vals.append(vals[-1] + d)

    with open(outfile, 'w') as out:
        start = 0
        for b in breaks:
            out.write(' '.join(str(x) for x in vals[start:b]) + '\n')
            start = b


def verify_compression(infile: str, compressed: str) -> None:
    # Decompress to temporary and compare
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    try:
        decompress_file(compressed, tmp.name)
        with open(infile, 'r') as f1, open(tmp.name, 'r') as f2:
            if f1.read() == f2.read():
                print("✔️ Verificación: los archivos coinciden")
            else:
                print("❌ Verificación: ¡ERROR, los archivos difieren!")
    finally:
        os.unlink(tmp.name)


def main():
    args = sys.argv[1:]
    verify_flag = False
    if '--verify' in args:
        verify_flag = True
        args.remove('--verify')

    if len(args) != 2:
        print("Usage: python3 compress.py infile outfile [--verify]")
        sys.exit(1)
    infile, outfile = args

    start = time.time()
    try:
        with open(infile, 'rb') as f:
            magic = f.read(4)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

    if magic == MAGIC:
        print("-> Modo descompresión")
        decompress_file(infile, outfile)
    else:
        print("-> Modo compresión")
        compress_file(infile, outfile)
        if verify_flag:
            verify_compression(infile, outfile)
    end = time.time()

    size_in = os.path.getsize(infile)
    size_out = os.path.getsize(outfile)
    elapsed = end - start
    speed = (size_in / 1024) / elapsed

    print(f"- Tiempo: {elapsed:.2f} s")
    print(f"- Tamaño entrada: {size_in/1024:.2f} kB")
    print(f"- Tamaño salida: {size_out/1024:.2f} kB")
    if magic != MAGIC:
        print(f"- Ratio de compresión: {size_in/size_out:.2f}x")
    print(f"- Velocidad: {speed:.2f} kB/s")

if __name__ == '__main__':
    main()
