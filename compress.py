#!/usr/bin/env python3
import struct
import math
import heapq
import sys
import os
import time
from collections import Counter

class BitWriter:
    def __init__(self, file):
        self.file = file
        self.accumulator = 0
        self.bits_filled = 0

    def write_bit(self, bit: int) -> None:
        self.accumulator = ((self.accumulator << 1) & 0xFF) | (bit & 1)
        self.bits_filled += 1
        if self.bits_filled == 8:
            self.file.write(bytes((self.accumulator,)))
            self.accumulator = 0
            self.bits_filled = 0

    def write_bits(self, bits: str) -> None:
        for b in bits:
            self.write_bit(int(b))

    def flush(self) -> None:
        if self.bits_filled > 0:
            self.accumulator <<= (8 - self.bits_filled)
            self.file.write(bytes((self.accumulator,)))
            self.accumulator = 0
            self.bits_filled = 0

class BitReader:
    def __init__(self, file):
        self.file = file
        self.accumulator = 0
        self.bits_remaining = 0

    def read_bit(self) -> int:
        if self.bits_remaining == 0:
            byte = self.file.read(1)
            if not byte:
                raise EOFError("Unexpected EOF in bitstream")
            self.accumulator = byte[0]
            self.bits_remaining = 8
        self.bits_remaining -= 1
        return (self.accumulator >> self.bits_remaining) & 1

    def read_bits(self, count: int) -> int:
        val = 0
        for _ in range(count):
            val = (val << 1) | self.read_bit()
        return val

class Compressor:
    MAGIC = b'ENHC'

    @staticmethod
    def zigzag_encode(n: int) -> int:
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def zigzag_decode(z: int) -> int:
        return (z >> 1) ^ -(z & 1)

    @staticmethod
    def gamma_encode(n: int) -> str:
        b = bin(n)[2:]
        return '0'*(len(b)-1) + b

    @staticmethod
    def gamma_decode(reader: BitReader) -> int:
        zeros = 0
        while reader.read_bit() == 0:
            zeros += 1
        val = 1 << zeros
        for i in range(zeros):
            val |= reader.read_bit() << (zeros - 1 - i)
        return val

    def compress_file(self, infile: str, outfile: str, rle_threshold: int = 4) -> None:
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
        n = len(vals)
        d1 = [vals[i] - vals[i-1] for i in range(1, n)]
        d2 = [d1[0]] + [d1[i] - d1[i-1] for i in range(1, len(d1))]
        zs = [self.zigzag_encode(d) for d in d2]
        RLE_SYM = max(zs) + 1
        sym_stream = []
        run_lengths = []
        i = 0
        while i < len(zs):
            if zs[i] == 0:
                run = 1
                while i+run < len(zs) and zs[i+run] == 0:
                    run += 1
                if run >= rle_threshold:
                    sym_stream.append(RLE_SYM)
                    run_lengths.append(run)
                    i += run
                    continue
            sym_stream.append(zs[i])
            i += 1
        freqs = Counter(sym_stream)
        total = sum(freqs.values())
        lengths = {sym: max(1, int(math.ceil(-math.log(freq/total, 2))))
                   for sym, freq in freqs.items()}
        sorted_syms = sorted(lengths.items(), key=lambda x: (x[1], x[0]))
        codes = {}
        code = 0
        prev_len = sorted_syms[0][1]
        for sym, length in sorted_syms:
            code <<= (length - prev_len)
            codes[sym] = format(code, f'0{length}b')
            code += 1
            prev_len = length
        with open(outfile, 'wb') as out:
            out.write(self.MAGIC)
            out.write(struct.pack('<I', n))
            out.write(struct.pack('<i', vals[0]))
            out.write(struct.pack('<I', len(breaks)))
            for b in breaks:
                out.write(struct.pack('<I', b))
            out.write(struct.pack('<I', len(lengths)))
            for sym, length in lengths.items():
                out.write(struct.pack('<I', sym))
                out.write(struct.pack('B', length))
            writer = BitWriter(out)
            rl_idx = 0
            for sym in sym_stream:
                writer.write_bits(codes[sym])
                if sym == RLE_SYM:
                    writer.write_bits(self.gamma_encode(run_lengths[rl_idx]))
                    rl_idx += 1
            writer.flush()

    def decompress_file(self, infile: str, outfile: str) -> None:
        with open(infile, 'rb') as inp:
            if inp.read(4) != self.MAGIC:
                raise ValueError("Not an ENHC file")
            n = struct.unpack('<I', inp.read(4))[0]
            h0 = struct.unpack('<i', inp.read(4))[0]
            nb = struct.unpack('<I', inp.read(4))[0]
            breaks = [struct.unpack('<I', inp.read(4))[0] for _ in range(nb)]
            st_count = struct.unpack('<I', inp.read(4))[0]
            lengths = {struct.unpack('<I', inp.read(4))[0]: inp.read(1)[0]
                       for _ in range(st_count)}
            sorted_syms = sorted(lengths.items(), key=lambda x: (x[1], x[0]))
            rev = {}
            code = 0
            prev_len = sorted_syms[0][1]
            for sym, length in sorted_syms:
                code <<= (length - prev_len)
                rev[format(code, f'0{length}b')] = sym
                code += 1
                prev_len = length
            reader = BitReader(inp)
            zs = []
            buf = ''
            RLE_SYM = max(lengths)
            while len(zs) < n-1:
                buf += str(reader.read_bit())
                if buf in rev:
                    sym = rev[buf]
                    buf = ''
                    if sym == RLE_SYM:
                        run = self.gamma_decode(reader)
                        zs.extend([0]*run)
                    else:
                        zs.append(sym)
        d2 = [self.zigzag_decode(z) for z in zs]
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

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 compress.py infile outfile")
        sys.exit(1)

    infile = sys.argv[1]
    outfile = sys.argv[2]

    compressor = Compressor()

    if infile.endswith('.txt'):
        print("-> Modo compresión")
        start = time.time()
        compressor.compress_file(infile, outfile)
        end = time.time()

        size_in = os.path.getsize(infile)
        size_out = os.path.getsize(outfile)
        elapsed = end - start
        ratio = size_in / size_out if size_out != 0 else float('inf')
        speed = (size_in / 1024) / elapsed

        print(f"- Compresión completada en {elapsed:.2f} s")
        print(f"- Tamaño original:   {size_in/1024:.2f} kB")
        print(f"- Tamaño comprimido: {size_out/1024:.2f} kB")
        print(f"- Ratio de compresión: {ratio:.2f}x")
        print(f"- Velocidad: {speed:.2f} kB/s")

    elif infile.endswith('.bin'):
        print("-> Modo descompresión")
        start = time.time()
        compressor.decompress_file(infile, outfile)
        end = time.time()

        size_in = os.path.getsize(infile)
        size_out = os.path.getsize(outfile)
        elapsed = end - start
        speed = (size_in / 1024) / elapsed

        print(f"- Descompresión completada en {elapsed:.2f} s")
        print(f"- Tamaño comprimido: {size_in/1024:.2f} kB")
        print(f"- Tamaño recuperado: {size_out/1024:.2f} kB")
        print(f"- Velocidad: {speed:.2f} kB/s")

    else:
        print("Error: el archivo debe terminar en .txt o .bin")
        sys.exit(1)

if __name__ == '__main__':
    main()
