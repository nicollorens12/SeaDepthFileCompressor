import struct
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

class HuffmanNode:
    def __init__(self, symbol=None, freq=0):
        self.symbol = symbol
        self.freq = freq
        self.left = None
        self.right = None
    def __lt__(self, other):
        return self.freq < other.freq

class HuffmanCompressor:
    """
    Compressor tailored for sea-height files with line breaks:
    - Deltas + zigzag
    - Huffman coding of non-negative symbols
    - Header includes line break positions for exact round-trip
    """
    MAGIC = b'HFMR'

    @staticmethod
    def zigzag_encode(n: int) -> int:
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def zigzag_decode(z: int) -> int:
        return (z >> 1) ^ -(z & 1)

    def build_tree(self, freqs: Counter) -> HuffmanNode:
        heap = [HuffmanNode(sym, fr) for sym, fr in freqs.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            a = heapq.heappop(heap)
            b = heapq.heappop(heap)
            parent = HuffmanNode(freq=a.freq + b.freq)
            parent.left, parent.right = a, b
            heapq.heappush(heap, parent)
        return heap[0]

    def gen_codes(self, node: HuffmanNode, prefix: str, table: dict) -> None:
        if node.symbol is not None:
            table[node.symbol] = prefix
        else:
            self.gen_codes(node.left, prefix + '0', table)
            self.gen_codes(node.right, prefix + '1', table)

    def write_tree(self, node: HuffmanNode, writer: BitWriter) -> None:
        if node.symbol is None:
            writer.write_bit(0)
            self.write_tree(node.left, writer)
            self.write_tree(node.right, writer)
        else:
            writer.write_bit(1)
            writer.write_bits(f'{node.symbol:032b}')

    def read_tree(self, reader: BitReader) -> HuffmanNode:
        bit = reader.read_bit()
        if bit == 1:
            sym = reader.read_bits(32)
            return HuffmanNode(symbol=sym)
        node = HuffmanNode()
        node.left = self.read_tree(reader)
        node.right = self.read_tree(reader)
        return node

    def compress_file(self, infile: str, outfile: str) -> None:
        # Read input, record line breaks
        values = []
        line_breaks = []
        count = 0
        with open(infile, 'r') as f:
            for line in f:
                nums = [int(x) for x in line.split()]
                values.extend(nums)
                count += len(nums)
                line_breaks.append(count)
        if not values:
            raise ValueError("Empty input file")
        # Deltas + zigzag
        deltas = [values[0]] + [values[i] - values[i-1] for i in range(1, len(values))]
        zs = [self.zigzag_encode(d) for d in deltas]
        # Build Huffman on zs[1:]
        freqs = Counter(zs[1:])
        tree = self.build_tree(freqs)
        codes = {}
        self.gen_codes(tree, '', codes)
        # Write
        with open(outfile, 'wb') as out:
            writer = BitWriter(out)
            out.write(self.MAGIC)
            out.write(struct.pack('<I', len(values)))       # total symbols
            out.write(struct.pack('<i', values[0]))         # h0
            out.write(struct.pack('<I', len(line_breaks)))  # num lines
            for pos in line_breaks:
                out.write(struct.pack('<I', pos))            # each break
            # tree and data
            self.write_tree(tree, writer)
            # encode data symbols zs[1:]
            for z in zs[1:]:
                writer.write_bits(codes[z])
            writer.flush()

    def decompress_file(self, infile: str, outfile: str) -> None:
        with open(infile, 'rb') as inp:
            magic = inp.read(4)
            if magic != self.MAGIC:
                raise ValueError("Not a HFMR file")
            n = struct.unpack('<I', inp.read(4))[0]
            h0 = struct.unpack('<i', inp.read(4))[0]
            num_lines = struct.unpack('<I', inp.read(4))[0]
            line_breaks = [struct.unpack('<I', inp.read(4))[0] for _ in range(num_lines)]
            reader = BitReader(inp)
            tree = self.read_tree(reader)
            # decode n-1 symbols into deltas
            zs = []
            node = tree
            while len(zs) < n-1:
                bit = reader.read_bit()
                node = node.right if bit else node.left
                if node.symbol is not None:
                    zs.append(node.symbol)
                    node = tree
            # reconstruct values
            vals = [h0]
            for z in zs:
                d = self.zigzag_decode(z)
                vals.append(vals[-1] + d)
        # write lines
        with open(outfile, 'w') as out:
            start = 0
            for br in line_breaks:
                line = vals[start:br]
                out.write(' '.join(str(x) for x in line) + '\n')
                start = br
