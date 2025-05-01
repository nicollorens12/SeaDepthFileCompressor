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
    Golomb-Rice compressor with optional run-length encoding of zero-symbols
    and second-order (delta-of-delta) coding for better compression ratio.
    """
    MAGIC = b'HTZR'
    RLE_THRESHOLD_FACTOR = 4  # minimal run = factor * 2^k

    def __init__(self, k=None, min_run=None):
        self.k = k
        self.min_run = min_run

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
        # Read heights
        with open(infile_path, 'r') as f:
            lines = f.readlines()
        heights = []
        line_breaks = []
        count = 0
        for line in lines:
            nums = [int(x) for x in line.split()]
            heights.extend(nums)
            count += len(nums)
            line_breaks.append(count)
        if not heights:
            raise ValueError("Input file is empty")

        n = len(heights)
        # First-order deltas
        d1 = [heights[i] - heights[i-1] for i in range(1, n)]  # length n-1
        # Second-order deltas (delta-of-delta)
        d2 = [d1[0]] + [d1[i] - d1[i-1] for i in range(1, len(d1))]
        # ZigZag encode
        zs = [self.zigzag_encode(d) for d in d2]  # length n-1

        # Choose k
        k = self.k if self.k is not None else self.choose_k(zs)
        # Determine RLE threshold
        min_run = self.min_run if self.min_run is not None else (self.RLE_THRESHOLD_FACTOR << k)
        # Detect longest zero-run
        longest = run = 0
        for z in zs:
            if z == 0:
                run += 1
                longest = max(longest, run)
            else:
                run = 0
        use_rle = (longest >= min_run)

        # Write header
        with open(outfile_path, 'wb') as out:
            out.write(self.MAGIC)
            out.write(struct.pack('<I', n))            # number of samples
            out.write(struct.pack('<i', heights[0]))  # h0
            out.write(struct.pack('B', k))            # parameter k
            out.write(struct.pack('B', 1 if use_rle else 0))
            out.write(struct.pack('<I', len(line_breaks)))
            for pos in line_breaks:
                out.write(struct.pack('<I', pos))

            writer = BitWriter(out)
            # Encode symbols
            idx = 0
            while idx < len(zs):
                if use_rle and zs[idx] == 0:
                    # run-length
                    run = 1
                    while idx+run < len(zs) and zs[idx+run] == 0:
                        run += 1
                    if run >= min_run:
                        # write zero-run token
                        writer.write_bit(0)
                        q = run >> k
                        r = run & ((1 << k) - 1)
                        for _ in range(q): writer.write_bit(1)
                        writer.write_bit(0)
                        if k>0: writer.write_bits(r, k)
                        idx += run
                        continue
                # raw symbol (flag=1)
                if use_rle:
                    writer.write_bit(1)
                z = zs[idx]
                q = z >> k
                r = z & ((1<<k) - 1)
                for _ in range(q): writer.write_bit(1)
                writer.write_bit(0)
                if k>0: writer.write_bits(r, k)
                idx += 1
            writer.flush()

    def decompress_file(self, infile_path, outfile_path):
        with open(infile_path, 'rb') as inp:
            magic = inp.read(4)
            if magic != self.MAGIC:
                raise ValueError("Not a HTZR-compressed file")
            n = struct.unpack('<I', inp.read(4))[0]
            h0 = struct.unpack('<i', inp.read(4))[0]
            k = inp.read(1)[0]
            use_rle = bool(inp.read(1)[0])
            num_lines = struct.unpack('<I', inp.read(4))[0]
            line_breaks = [struct.unpack('<I', inp.read(4))[0] for _ in range(num_lines)]

            reader = BitReader(inp)
            zs = []  # recovered zigzag values
            while len(zs) < n-1:
                if use_rle:
                    flag = reader.read_bit()
                    if flag == 0:
                        # zero-run
                        q = 0
                        while reader.read_bit(): q += 1
                        r = reader.read_bits(k) if k>0 else 0
                        run = (q<<k) | r
                        zs.extend([0]*run)
                        continue
                # raw symbol or non-RLE
                # if non-RLE, previous bit is part of unary
                q = 0
                while reader.read_bit(): q += 1
                r = reader.read_bits(k) if k>0 else 0
                zs.append((q<<k) | r)

        # Recover deltas
        # d2 = decoded ZigZag values
        d2 = [self.zigzag_decode(z) for z in zs]
        # recover d1 (length n-1)
        d1 = [d2[0]]
        for i in range(1, len(d2)):
            d1.append(d2[i] + d1[i-1])
        # recover heights
        heights = [h0]
        for delta in d1:
            heights.append(heights[-1] + delta)

        # write output
        with open(outfile_path, 'w') as out:
            start = 0
            for end in line_breaks:
                out.write(' '.join(str(h) for h in heights[start:end]) + '\n')
                start = end

# Example usage:
# comp = SolCompressor()
# comp.compress_file('ShortFile111111.txt', 'out.bin')
# comp.decompress_file('out.bin', 'recovered.txt')
