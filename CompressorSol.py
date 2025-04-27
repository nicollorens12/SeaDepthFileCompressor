import struct
import math

class BitWriter:
    def __init__(self, file):
        self.file = file
        self.accumulator = 0
        self.bits_filled = 0

    def write_bit(self, bit):
        if bit not in (0, 1):
            raise ValueError("Bit must be 0 or 1")
        self.accumulator = (self.accumulator << 1) | bit
        self.bits_filled += 1
        if self.bits_filled == 8:
            self.file.write(bytes((self.accumulator,)))
            self.accumulator = 0
            self.bits_filled = 0

    def write_bits(self, value, count):
        for i in reversed(range(count)):
            self.write_bit((value >> i) & 1)

    def flush(self):
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

    def read_bit(self):
        if self.bits_remaining == 0:
            byte = self.file.read(1)
            if not byte:
                raise EOFError("No more bits to read")
            self.accumulator = byte[0]
            self.bits_remaining = 8
        self.bits_remaining -= 1
        return (self.accumulator >> self.bits_remaining) & 1

    def read_bits(self, count):
        value = 0
        for _ in range(count):
            value = (value << 1) | self.read_bit()
        return value

class SolCompressor:
    """
    Golomb-Rice compressor with optional run-length encoding of zero-symbols.
    Switches to plain Golomb-Rice if no long zero runs are detected.
    """
    MAGIC = b'HTZR'
    RLE_THRESHOLD_FACTOR = 4  # multiplier for minimal run length: run >= factor*2^k

    def __init__(self, k=None, min_run=None):
        self.k = k  # explicit k or None to auto-choose
        self.min_run = min_run  # override minimal run threshold

    @staticmethod
    def zigzag_encode(n):
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def zigzag_decode(z):
        return (z >> 1) ^ -(z & 1)

    def choose_k(self, values):
        mean = sum(values) / len(values) if values else 0
        return max(0, int(round(math.log2(mean + 1))))

    def compress_file(self, infile_path, outfile_path):
        # Read heights and line breaks
        with open(infile_path, 'r') as f:
            lines = f.readlines()

        all_heights, line_breaks = [], []
        counter = 0
        for line in lines:
            nums = [int(x) for x in line.split()]
            all_heights.extend(nums)
            counter += len(nums)
            line_breaks.append(counter)

        if not all_heights:
            raise ValueError("Input file is empty")

        n = len(all_heights)
        deltas = [all_heights[0]] + [all_heights[i] - all_heights[i-1] for i in range(1, n)]
        zs = [self.zigzag_encode(d) for d in deltas]

        # Determine k
        k = self.k if self.k is not None else self.choose_k(zs[1:])
        # Determine minimal run threshold
        min_run = self.min_run if self.min_run is not None else (self.RLE_THRESHOLD_FACTOR << k)

        # Scan for long zero-runs
        longest_run = 0
        run = 0
        for z in zs[1:]:
            if z == 0:
                run += 1
                longest_run = max(longest_run, run)
            else:
                run = 0
        use_rle = (longest_run >= min_run)

        with open(outfile_path, 'wb') as out:
            # Header: MAGIC, count, h0, k, rle_flag, num_lines, line_breaks...
            out.write(self.MAGIC)
            out.write(struct.pack('<I', n))
            out.write(struct.pack('<i', all_heights[0]))
            out.write(struct.pack('B', k))
            out.write(struct.pack('B', 1 if use_rle else 0))
            out.write(struct.pack('<I', len(line_breaks)))
            for pos in line_breaks:
                out.write(struct.pack('<I', pos))

            writer = BitWriter(out)
            if not use_rle:
                # Plain Golomb-Rice
                for z in zs[1:]:
                    q = z >> k
                    r = z & ((1 << k) - 1)
                    for _ in range(q): writer.write_bit(1)
                    writer.write_bit(0)
                    if k > 0:
                        writer.write_bits(r, k)
                writer.flush()
                return

            # RLE-enabled encoding
            i = 1
            while i < len(zs):
                if zs[i] == 0:
                    # Count zero-run
                    run = 1
                    while i + run < len(zs) and zs[i + run] == 0:
                        run += 1
                    if run >= min_run:
                        # Token: zero-run
                        writer.write_bit(0)
                        q = run >> k
                        r = run & ((1 << k) - 1)
                        for _ in range(q): writer.write_bit(1)
                        writer.write_bit(0)
                        if k > 0:
                            writer.write_bits(r, k)
                        i += run
                        continue
                # Raw single symbol
                writer.write_bit(1)
                z = zs[i]
                q = z >> k
                r = z & ((1 << k) - 1)
                for _ in range(q): writer.write_bit(1)
                writer.write_bit(0)
                if k > 0:
                    writer.write_bits(r, k)
                i += 1
            writer.flush()

    def decompress_file(self, infile_path, outfile_path):
        with open(infile_path, 'rb') as inp:
            magic = inp.read(4)
            if magic != self.MAGIC:
                raise ValueError("Not a HTZR-compressed file")
            n = struct.unpack('<I', inp.read(4))[0]
            h0 = struct.unpack('<i', inp.read(4))[0]
            k = struct.unpack('B', inp.read(1))[0]
            use_rle = bool(inp.read(1)[0])
            num_lines = struct.unpack('<I', inp.read(4))[0]
            line_breaks = [struct.unpack('<I', inp.read(4))[0] for _ in range(num_lines)]

            reader = BitReader(inp)
            heights = [h0]
            if not use_rle:
                # Plain decode
                for _ in range(n-1):
                    q = 0
                    while reader.read_bit(): q += 1
                    # unary stop bit consumed as 0
                    r = reader.read_bits(k) if k > 0 else 0
                    z = (q << k) | r
                    d = self.zigzag_decode(z)
                    heights.append(heights[-1] + d)
            else:
                # RLE decode
                while len(heights) < n:
                    pbit = reader.read_bit()
                    if pbit == 0:
                        # zero-run token
                        q = 0
                        while reader.read_bit(): q += 1
                        r = reader.read_bits(k) if k > 0 else 0
                        run = (q << k) | r
                        heights.extend([heights[-1]] * run)
                    else:
                        q = 0
                        while reader.read_bit(): q += 1
                        r = reader.read_bits(k) if k > 0 else 0
                        z = (q << k) | r
                        d = self.zigzag_decode(z)
                        heights.append(heights[-1] + d)

        # Write back with original line breaks
        with open(outfile_path, 'w') as out:
            start = 0
            for end in line_breaks:
                out.write(' '.join(str(h) for h in heights[start:end]) + '\n')
                start = end

# Example usage:
# comp = GolombRiceCompressorRLE()
# comp.compress_file('ShortFile111111.txt', 'out.bin')
# comp.decompress_file('out.bin', 'recovered.txt')
