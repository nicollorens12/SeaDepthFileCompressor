import struct
import math
import heapq
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

class SolCompressor:
    """
    Compressor combining:
      - Second-order delta-of-delta + ZigZag
      - Zero-run RLE with Elias gamma coding
      - Canonical Huffman coding of final symbol stream
    """
    MAGIC = b'ENHC'

    @staticmethod
    def zigzag_encode(n: int) -> int:
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def zigzag_decode(z: int) -> int:
        return (z >> 1) ^ -(z & 1)

    @staticmethod
    def gamma_encode(n: int) -> str:
        # Elias gamma for n>=1
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
        # Read values and line breaks
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
        # First and second-order deltas
        d1 = [vals[i] - vals[i-1] for i in range(1, n)]
        d2 = [d1[0]] + [d1[i] - d1[i-1] for i in range(1, len(d1))]
        zs = [self.zigzag_encode(d) for d in d2]
        # Prepare RLE symbol and streams
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
        # Build canonical Huffman codes
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
        # Write header, symbol table, then data
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
            RLE_SYM = max(lengths)  # assume the largest symbol is RLE
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
        # Invert transforms
        d2 = [self.zigzag_decode(z) for z in zs]
        d1 = [d2[0]]
        for i in range(1, len(d2)):
            d1.append(d2[i] + d1[i-1])
        vals = [h0]
        for d in d1:
            vals.append(vals[-1] + d)
        # Write output
        with open(outfile, 'w') as out:
            start = 0
            for b in breaks:
                out.write(' '.join(str(x) for x in vals[start:b]) + '\n')
                start = b

# Usage example:
# comp = EnhancedCompressor()
# comp.compress_file('in.txt','out.bin')
# comp.decompress_file('out.bin','out.txt')