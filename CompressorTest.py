import struct
import math
import os

class BitWriter:
    def __init__(self, file):
        self.file = file
        self.accumulator = 0
        self.bits_filled = 0

    def write_bit(self, bit):
        if bit not in (0,1): raise ValueError("Bit must be 0 or 1")
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
            if not byte: raise EOFError("No more bits to read")
            self.accumulator = byte[0]
            self.bits_remaining = 8
        self.bits_remaining -= 1
        return (self.accumulator >> self.bits_remaining) & 1

    def read_bits(self, count):
        value = 0
        for _ in range(count): value = (value << 1) | self.read_bit()
        return value

class GolombRiceEnhanced:
    MAGIC = b'HTZ1'
    BLOCK_SIZE = 1024       # valores por bloque
    RUN_THRESHOLD = 4       # mínimo ceros para usar run-length

    def __init__(self, k=None):
        self.k_global = k

    @staticmethod
    def zigzag_encode(n): return (n << 1) ^ (n >> 31)
    @staticmethod
    def zigzag_decode(z): return (z >> 1) ^ -(z & 1)

    def choose_k(self, vals):
        mean = sum(vals)/len(vals) if vals else 0
        return max(0, int(round(math.log2(mean+1))))

    def compress_file(self, infile, outfile):
        # Leer y aplanar
        with open(infile,'r') as f:
            data = [int(x) for line in f for x in line.split()]
        n = len(data)
        if n==0: raise ValueError("Empty file")
        # Delta + ZigZag
        deltas = [data[0]] + [data[i]-data[i-1] for i in range(1,n)]
        zs = [self.zigzag_encode(d) for d in deltas]
        # Header global
        with open(outfile,'wb') as out:
            out.write(self.MAGIC)
            out.write(struct.pack('<I',n))
            out.write(struct.pack('<i',data[0]))
            out.write(struct.pack('<I',self.BLOCK_SIZE))
            writer = BitWriter(out)
            # Procesar bloques
            for bstart in range(1,n, self.BLOCK_SIZE):
                bend = min(bstart+self.BLOCK_SIZE, n)
                block = zs[bstart:bend]
                k = self.k_global if self.k_global is not None else self.choose_k(block)
                # Escribir k y len(bloque)
                out.write(struct.pack('B',k))
                out.write(struct.pack('<I',len(block)))
                # Codificar con run-length de ceros + Rice
                i=0
                while i < len(block):
                    if block[i]==0:
                        # contar corrida
                        j=i
                        while j<len(block) and block[j]==0: j+=1
                        run = j-i
                        if run>=self.RUN_THRESHOLD:
                            writer.write_bit(1)           # flag run
                            writer.write_bits(run,16)
                            i=j
                            continue
                    # valor normal
                    writer.write_bit(0)               # flag normal
                    z=block[i]
                    q=z>>k; r=z & ((1<<k)-1)
                    for _ in range(q): writer.write_bit(1)
                    writer.write_bit(0)
                    writer.write_bits(r,k)
                    i+=1
            writer.flush()

    def decompress_file(self, infile, outfile):
        with open(infile,'rb') as inp:
            if inp.read(4)!=self.MAGIC: raise ValueError("Invalid file")
            n=struct.unpack('<I',inp.read(4))[0]
            h0=struct.unpack('<i',inp.read(4))[0]
            block_size=struct.unpack('<I',inp.read(4))[0]
            reader=BitReader(inp)
            data=[h0]
            # Leer bloques
            while len(data)<n:
                k=struct.unpack('B',inp.read(1))[0]
                blen=struct.unpack('<I',inp.read(4))[0]
                count=0
                while count<blen:
                    flag=reader.read_bit()
                    if flag==1:
                        run=reader.read_bits(16)
                        for _ in range(run): data.append(data[-1])
                        count+=run
                    else:
                        # leer Rice
                        q=0
                        while reader.read_bit(): q+=1
                        r=reader.read_bits(k) if k>0 else 0
                        z=(q<<k)|r
                        d=self.zigzag_decode(z)
                        data.append(data[-1]+d)
                        count+=1
        # Escribir plano
        with open(outfile,'w') as out:
            out.write(' '.join(str(x) for x in data))

# Uso:
# comp=GolombRiceEnhanced()\# comp.compress_file('in.txt','out.bin')
# comp.decompress_file('out.bin','rec.txt')
