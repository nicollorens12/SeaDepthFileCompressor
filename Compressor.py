import struct
import math

class BitWriter:
    def __init__(self, file):
        self.file = file
        self.accumulator = 0
        self.bits_filled = 0

    def write_bit(self, bit):
        if bit not in (0,1):
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

class GolombRiceCompressor:
    MAGIC = b'HTZ1'

    def __init__(self, k=None):
        # If k is None, compute optimum k dynamically during compression
        self.k = k

    @staticmethod
    def zigzag_encode(n):
        return (n << 1) ^ (n >> 31)

    @staticmethod
    def zigzag_decode(z):
        return (z >> 1) ^ -(z & 1)

    def choose_k(self, values):
        # Choose k based on mean of z values
        mean = sum(values) / len(values) if values else 0
        return max(0, int(round(math.log2(mean + 1))))

    def compress_file(self, infile_path, outfile_path):
        # Leer las alturas manteniendo la estructura de líneas
        with open(infile_path, 'r') as f:
            lines = f.readlines()
        
        # Procesar cada línea y mantener la estructura
        all_heights = []
        line_breaks = []  # Para guardar dónde van los saltos de línea
        count = 0
        
        for line in lines:
            heights_in_line = [int(x) for x in line.split()]
            all_heights.extend(heights_in_line)
            count += len(heights_in_line)
            line_breaks.append(count)  # Guardamos el índice después del último número de cada línea
        
        if not all_heights:
            raise ValueError("Input file is empty")
        
        n = len(all_heights)
        num_lines = len(line_breaks)
        
        # Delta coding
        deltas = [all_heights[0]] + [all_heights[i] - all_heights[i-1] for i in range(1, n)]
        
        # ZigZag encoding
        zs = [self.zigzag_encode(d) for d in deltas]
        
        # Decide k
        k = self.k if self.k is not None else self.choose_k(zs[1:])
        
        # Write header and bitstream
        with open(outfile_path, 'wb') as out:
            out.write(self.MAGIC)
            out.write(struct.pack('<I', n))
            out.write(struct.pack('<i', all_heights[0]))
            out.write(struct.pack('B', k))
            
            # Guardar la cantidad de líneas y posiciones de saltos
            out.write(struct.pack('<I', num_lines))
            for pos in line_breaks:
                out.write(struct.pack('<I', pos))
            
            writer = BitWriter(out)
            for z in zs[1:]:
                q = z >> k
                r = z & ((1 << k) - 1)
                # Write q ones and a zero
                for _ in range(q): writer.write_bit(1)
                writer.write_bit(0)
                # Write remainder r in k bits
                writer.write_bits(r, k)
            writer.flush()

    def decompress_file(self, infile_path, outfile_path):
        with open(infile_path, 'rb') as inp:
            magic = inp.read(4)
            if magic != self.MAGIC:
                raise ValueError("Not a HTZ1-compressed file")
            n = struct.unpack('<I', inp.read(4))[0]
            h0 = struct.unpack('<i', inp.read(4))[0]
            k = struct.unpack('B', inp.read(1))[0]
            
            # Leer información de saltos de línea
            num_lines = struct.unpack('<I', inp.read(4))[0]
            line_breaks = []
            for _ in range(num_lines):
                pos = struct.unpack('<I', inp.read(4))[0]
                line_breaks.append(pos)
            
            reader = BitReader(inp)
            heights = [h0]
            for _ in range(n-1):
                # Read unary quotient q
                q = 0
                while True:
                    bit = reader.read_bit()
                    if bit == 0:
                        break
                    q += 1
                r = reader.read_bits(k) if k > 0 else 0
                z = (q << k) | r
                d = self.zigzag_decode(z)
                heights.append(heights[-1] + d)
        
        # Escribir alturas respetando los saltos de línea
        with open(outfile_path, 'w') as out:
            start = 0
            for end in line_breaks:
                line_heights = heights[start:end]
                out.write(' '.join(str(h) for h in line_heights) + '\n')
                start = end

# Ejemplo de uso:
# comp = GolombRiceCompressor()
# comp.compress_file('file11111.txt', 'out.bin')
# comp.decompress_file('out.bin', 'recovered.txt')
