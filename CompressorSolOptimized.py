import struct
import math
import heapq
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
            # Caso especial: un solo símbolo
            symbol = list(frequencies.keys())[0]
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
                codes[node.symbol] = code if code else '0'
            else:
                if node.left:
                    assign_codes(node.left, code + '0')
                if node.right:
                    assign_codes(node.right, code + '1')
        
        assign_codes(root)
        return codes

    def encode_runs_adaptive(self, symbols):
        """RLE mejorado que detecta patrones de repetición de cualquier símbolo"""
        # Encontrar el símbolo menos frecuente para usar como marcador
        freq = Counter(symbols)
        escape_symbol = max(freq.keys()) + 1
        
        result = []
        runs_data = []
        i = 0
        
        while i < len(symbols):
            current = symbols[i]
            run_length = 1
            
            # Contar cuántos símbolos consecutivos iguales hay
            while i + run_length < len(symbols) and symbols[i + run_length] == current:
                run_length += 1
            
            # Decidir si codificar como run o literalmente
            if run_length >= 4:  # Umbral dinámico
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
        
        # Para valores pequeños, usar menos bits
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
        
        if reader.read_bit() == 0:  # 10
            return reader.read_bits(4)
        elif reader.read_bit() == 0:  # 110
            return reader.read_bits(8)
        elif reader.read_bit() == 0:  # 1110
            return reader.read_bits(16)
        else:  # 1111
            return reader.read_bits(32)

    def compress_file(self, infile: str, outfile: str) -> None:
        # Leer datos preservando estructura de líneas
        vals = []
        line_lengths = []
        
        with open(infile, 'r') as f:
            for line in f:
                nums = [int(x) for x in line.split()]
                vals.extend(nums)
                line_lengths.append(len(nums))
        
        if not vals:
            raise ValueError("Empty input file")
        
        n = len(vals)
        
        # Aplicar transformaciones predictivas
        # Delta de primer orden
        d1 = [vals[i] - vals[i-1] for i in range(1, n)]
        
        # Delta de segundo orden
        d2 = [d1[0]] + [d1[i] - d1[i-1] for i in range(1, len(d1))]
        
        # ZigZag encoding
        zs = [self.zigzag_encode(d) for d in d2]
        
        # RLE mejorado
        compressed_symbols, runs_data, escape_symbol = self.encode_runs_adaptive(zs)
        
        # Huffman óptimo
        frequencies = Counter(compressed_symbols)
        huffman_codes = self.build_optimal_huffman(frequencies)
        
        # Escribir archivo comprimido
        with open(outfile, 'wb') as out:
            # Header
            out.write(self.MAGIC)
            out.write(struct.pack('<I', n))
            out.write(struct.pack('<i', vals[0]))  # Primer valor
            
            # Estructura de líneas
            out.write(struct.pack('<I', len(line_lengths)))
            for length in line_lengths:
                out.write(struct.pack('<I', length))
            
            # Información de RLE
            out.write(struct.pack('<I', escape_symbol))
            out.write(struct.pack('<I', len(runs_data)))
            
            # Tabla Huffman
            out.write(struct.pack('<I', len(huffman_codes)))
            for symbol, code in huffman_codes.items():
                out.write(struct.pack('<I', symbol))
                out.write(struct.pack('<B', len(code)))
                # Escribir el código como bytes
                padded_code = code.ljust((len(code) + 7) // 8 * 8, '0')
                for i in range(0, len(padded_code), 8):
                    byte_val = int(padded_code[i:i+8], 2)
                    out.write(struct.pack('<B', byte_val))
            
            # Datos comprimidos
            writer = BitWriter(out)
            run_idx = 0
            
            for symbol in compressed_symbols:
                writer.write_bits(huffman_codes[symbol])
                
                if symbol == escape_symbol:
                    original_symbol, run_length = runs_data[run_idx]
                    # Codificar símbolo original
                    writer.write_bits(huffman_codes.get(original_symbol, '0'))
                    # Codificar longitud del run
                    writer.write_bits(self.encode_variable_length(run_length))
                    run_idx += 1
            
            writer.flush()

    def decompress_file(self, infile: str, outfile: str) -> None:
        with open(infile, 'rb') as inp:
            # Leer header
            if inp.read(4) != self.MAGIC:
                raise ValueError("Not an IMPR file")
            
            n = struct.unpack('<I', inp.read(4))[0]
            first_val = struct.unpack('<i', inp.read(4))[0]
            
            # Estructura de líneas
            num_lines = struct.unpack('<I', inp.read(4))[0]
            line_lengths = []
            for _ in range(num_lines):
                line_lengths.append(struct.unpack('<I', inp.read(4))[0])
            
            # Información RLE
            escape_symbol = struct.unpack('<I', inp.read(4))[0]
            num_runs = struct.unpack('<I', inp.read(4))[0]
            
            # Tabla Huffman
            num_codes = struct.unpack('<I', inp.read(4))[0]
            codes_to_symbols = {}
            
            for _ in range(num_codes):
                symbol = struct.unpack('<I', inp.read(4))[0]
                code_length = struct.unpack('<B', inp.read(1))[0]
                
                # Leer código
                num_bytes = (code_length + 7) // 8
                code_bits = ''
                for _ in range(num_bytes):
                    byte_val = struct.unpack('<B', inp.read(1))[0]
                    code_bits += format(byte_val, '08b')
                
                code = code_bits[:code_length]
                codes_to_symbols[code] = symbol
            
            # Decodificar datos
            reader = BitReader(inp)
            zs = []
            
            try:
                while len(zs) < n - 1:
                    # Leer código Huffman
                    code = ''
                    while code not in codes_to_symbols:
                        code += str(reader.read_bit())
                    
                    symbol = codes_to_symbols[code]
                    
                    if symbol == escape_symbol:
                        # Leer símbolo original
                        orig_code = ''
                        while orig_code not in codes_to_symbols:
                            orig_code += str(reader.read_bit())
                        original_symbol = codes_to_symbols[orig_code]
                        
                        # Leer longitud del run
                        run_length = self.decode_variable_length(reader)
                        
                        # Expandir run
                        zs.extend([original_symbol] * run_length)
                    else:
                        zs.append(symbol)
            except EOFError:
                pass
        
        # Reconstruir valores originales
        d2 = [self.zigzag_decode(z) for z in zs]
        
        # Reconstruir delta de primer orden
        d1 = [d2[0]]
        for i in range(1, len(d2)):
            d1.append(d2[i] + d1[i-1])
        
        # Reconstruir valores originales
        vals = [first_val]
        for d in d1:
            vals.append(vals[-1] + d)
        
        # Escribir archivo de salida preservando estructura
        with open(outfile, 'w') as out:
            val_idx = 0
            for line_length in line_lengths:
                line_vals = vals[val_idx:val_idx + line_length]
                out.write(' '.join(str(v) for v in line_vals) + '\n')
                val_idx += line_length

# Uso
# compressor.compress_file('input.txt', 'output.bin')
# compressor.decompress_file('output.bin', 'reconstructed.txt')

