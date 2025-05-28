import struct
import math
import heapq
import sys
import os
import time
from collections import Counter, defaultdict

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

    def write_uint(self, value: int, bits: int) -> None:
        for i in range(bits-1, -1, -1):
            self.write_bit((value >> i) & 1)

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

    def read_uint(self, bits: int) -> int:
        return self.read_bits(bits)

class Node:
    def __init__(self, freq, symbol=None, left=None, right=None):
        self.freq = freq
        self.symbol = symbol
        self.left = left
        self.right = right
    
    def __lt__(self, other):
        return self.freq < other.freq

class ImprovedCompressor:
    """
    Compresor mejorado con:
    - Huffman óptimo (heap-based)
    - RLE multi-símbolo
    - Codificación adaptativa de runs
    - Optimización de predicción
    """
    MAGIC = b'IMPR'

    @staticmethod
    def zigzag_encode(n: int) -> int:
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def zigzag_decode(z: int) -> int:
        return (z >> 1) ^ -(z & 1)

    @staticmethod
    def build_optimal_huffman(frequencies):
        """Construye códigos Huffman óptimos usando heap"""
        if len(frequencies) <= 1:
            symbol = next(iter(frequencies))
            return {symbol: '0'}
        heap = [Node(freq, symbol) for symbol, freq in frequencies.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            merged = Node(left.freq + right.freq, left=left, right=right)
            heapq.heappush(heap, merged)
        root = heap[0]
        codes = {}
        def assign_codes(node, code=''):
            if node.symbol is not None:
                codes[node.symbol] = code or '0'
            else:
                assign_codes(node.left, code + '0')
                assign_codes(node.right, code + '1')
        assign_codes(root)
        return codes

    def encode_runs_adaptive(self, symbols):
        """RLE mejorado que detecta patrones de repetición de cualquier símbolo"""
        freq = Counter(symbols)
        escape_symbol = max(freq.keys()) + 1
        result = []
        runs_data = []
        i = 0
        while i < len(symbols):
            current = symbols[i]
            run_length = 1
            while i + run_length < len(symbols) and symbols[i + run_length] == current:
                run_length += 1
            if run_length >= 4:
                result.append(escape_symbol)
                runs_data.append((current, run_length))
                i += run_length
            else:
                result.append(current)
                i += 1
        return result, runs_data, escape_symbol

    def encode_variable_length(self, value):
        """Codificación de longitud variable mejorada"""
        if value == 0:
            return '0'
        if value < 16:
            return '10' + format(value, '04b')
        elif value < 256:
            return '110' + format(value, '08b')
        elif value < 65536:
            return '1110' + format(value, '016b')
        else:
            return '1111' + format(value, '032b')

    def decode_variable_length(self, reader):
        """Decodificación de longitud variable"""
        if reader.read_bit() == 0:
            return 0
        if reader.read_bit() == 0:
            return reader.read_bits(4)
        elif reader.read_bit() == 0:
            return reader.read_bits(8)
        elif reader.read_bit() == 0:
            return reader.read_bits(16)
        else:
            return reader.read_bits(32)

    def compress_file(self, infile: str, outfile: str) -> None:
        vals = []
        line_lengths = []
        with open(infile, 'r') as f:
            for line in f:
                nums = list(map(int, line.split()))
                vals.extend(nums)
                line_lengths.append(len(nums))
        if not vals:
            raise ValueError("Empty input file")
        n = len(vals)

        d1 = [vals[i] - vals[i-1] for i in range(1, n)]
        d2 = [d1[0]] + [d1[i] - d1[i-1] for i in range(1, len(d1))]
        zs = [self.zigzag_encode(d) for d in d2]

        compressed_symbols, runs_data, escape_symbol = self.encode_runs_adaptive(zs)
        frequencies = Counter(compressed_symbols)
        huffman_codes = self.build_optimal_huffman(frequencies)

        with open(outfile, 'wb') as out:
            out.write(self.MAGIC)
            out.write(struct.pack('<I', n))
            out.write(struct.pack('<i', vals[0]))

            out.write(struct.pack('<I', len(line_lengths)))
            for length in line_lengths:
                out.write(struct.pack('<I', length))

            out.write(struct.pack('<I', escape_symbol))
            out.write(struct.pack('<I', len(runs_data)))

            out.write(struct.pack('<I', len(huffman_codes)))
            for sym, code in huffman_codes.items():
                out.write(struct.pack('<I', sym))
                out.write(struct.pack('<B', len(code)))
                padded = code.ljust((len(code)+7)//8*8, '0')
                for i in range(0, len(padded), 8):
                    out.write(struct.pack('<B', int(padded[i:i+8], 2)))

            writer = BitWriter(out)
            run_idx = 0
            for sym in compressed_symbols:
                writer.write_bits(huffman_codes[sym])
                if sym == escape_symbol:
                    orig, run_len = runs_data[run_idx]
                    writer.write_bits(huffman_codes.get(orig, '0'))
                    writer.write_bits(self.encode_variable_length(run_len))
                    run_idx += 1
            writer.flush()

    def decompress_file(self, infile: str, outfile: str) -> None:
        with open(infile, 'rb') as inp:
            if inp.read(4) != self.MAGIC:
                raise ValueError("Not an IMPR file")
            n = struct.unpack('<I', inp.read(4))[0]
            first_val = struct.unpack('<i', inp.read(4))[0]

            num_lines = struct.unpack('<I', inp.read(4))[0]
            line_lengths = [struct.unpack('<I', inp.read(4))[0] for _ in range(num_lines)]

            escape_symbol = struct.unpack('<I', inp.read(4))[0]
            num_runs = struct.unpack('<I', inp.read(4))[0]

            num_codes = struct.unpack('<I', inp.read(4))[0]
            codes_to_symbols = {}
            for _ in range(num_codes):
                sym = struct.unpack('<I', inp.read(4))[0]
                length = struct.unpack('<B', inp.read(1))[0]
                bits = ''
                for _ in range((length+7)//8):
                    bits += format(struct.unpack('<B', inp.read(1))[0], '08b')
                codes_to_symbols[bits[:length]] = sym

            reader = BitReader(inp)
            zs = []
            while len(zs) < n-1:
                code = ''
                while code not in codes_to_symbols:
                    code += str(reader.read_bit())
                sym = codes_to_symbols[code]
                if sym == escape_symbol:
                    orig_code = ''
                    while orig_code not in codes_to_symbols:
                        orig_code += str(reader.read_bit())
                    orig = codes_to_symbols[orig_code]
                    run_len = self.decode_variable_length(reader)
                    zs.extend([orig]*run_len)
                else:
                    zs.append(sym)

        d2 = [self.zigzag_decode(z) for z in zs]
        d1 = [d2[0]]
        for i in range(1, len(d2)):
            d1.append(d2[i] + d1[i-1])
        vals = [first_val]
        for delta in d1:
            vals.append(vals[-1] + delta)

        with open(outfile, 'w') as out:
            idx = 0
            for length in line_lengths:
                line_vals = vals[idx:idx+length]
                out.write(' '.join(map(str, line_vals)) + '\n')
                idx += length

# Example usage:
# comp = ImprovedCompressor()
# comp.compress_file('input.txt', 'output.bin')
# comp.decompress_file('output.bin', 'output.txt')
