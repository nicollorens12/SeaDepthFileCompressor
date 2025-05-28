#!/usr/bin/env python3
import struct
import math
import sys
import os
import time
import lzma
import tempfile
from io import BytesIO

# Magic header for our 2D Paeth LZMA-based compressor
MAGIC = b'P2DL'
FLAG_VARIABLE_LINE_LENGTHS = b'\x00'
FLAG_UNIFORM_LINE_LENGTHS = b'\x01'

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

# Paeth Predictor
def paeth_predict(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c

# Compressor
def compress_file(infile: str, outfile:str) -> None:
    data_rows = []
    with open(infile, 'r') as f:
        for line in f:
            stripped_line = line.strip()
            nums = []
            if stripped_line:
                try:
                    nums = [int(x) for x in stripped_line.split()]
                except ValueError:
                    print(f"Warning: Skipping line with non-integer data: '{line.strip()}'", file=sys.stderr)
                    # nums remains []
            data_rows.append(nums)

    num_rows = len(data_rows)
    line_lengths = [len(row) for row in data_rows]
    
    _vals_flat = [val for row in data_rows for val in row]
    actual_total_values = len(_vals_flat)

    with open(outfile, 'wb') as out:
        out.write(MAGIC)
        out.write(struct.pack('<I', num_rows))

        if num_rows > 0:
            first_length = line_lengths[0]
            are_all_lengths_same = all(l == first_length for l in line_lengths)
            if are_all_lengths_same:
                out.write(FLAG_UNIFORM_LINE_LENGTHS)
                out.write(write_varint(first_length))
            else:
                out.write(FLAG_VARIABLE_LINE_LENGTHS)
                for length in line_lengths:
                    out.write(write_varint(length))
        # If num_rows is 0, no length information needs to be written beyond this point.

        if actual_total_values == 0:
            return

        h0 = _vals_flat[0]
        out.write(write_varint(zigzag_encode(h0)))

        if actual_total_values == 1:
            return

        deltas_to_encode = []
        reconstructed_rows_for_pred = []

        for r, current_actual_row_values in enumerate(data_rows):
            current_processing_row_for_reconstruction = []
            prev_reconstructed_full_row = reconstructed_rows_for_pred[r-1] if r > 0 else None

            for c, actual_val in enumerate(current_actual_row_values):
                if r == 0 and c == 0: # h0
                    current_processing_row_for_reconstruction.append(actual_val)
                    continue
                
                val_A = current_processing_row_for_reconstruction[c-1] if c > 0 else None
                val_B = None
                if prev_reconstructed_full_row and c < len(prev_reconstructed_full_row):
                    val_B = prev_reconstructed_full_row[c]
                
                val_C = None
                if prev_reconstructed_full_row and c > 0 and (c-1) < len(prev_reconstructed_full_row):
                    val_C = prev_reconstructed_full_row[c-1]

                pred = 0
                if val_A is not None and val_B is not None and val_C is not None:
                    pred = paeth_predict(val_A, val_B, val_C)
                elif val_A is not None:
                    pred = val_A
                elif val_B is not None:
                    pred = val_B
                
                delta = actual_val - pred
                deltas_to_encode.append(delta)
                current_processing_row_for_reconstruction.append(actual_val)
            
            reconstructed_rows_for_pred.append(current_processing_row_for_reconstruction)

        if deltas_to_encode:
            raw_deltas_payload = bytearray()
            for d_val in deltas_to_encode:
                raw_deltas_payload.extend(write_varint(zigzag_encode(d_val)))
            
            if raw_deltas_payload:
                compressed_deltas = lzma.compress(bytes(raw_deltas_payload), preset=(9 | lzma.PRESET_EXTREME))
                out.write(compressed_deltas)

# Decompressor
def decompress_file(infile: str, outfile: str) -> None:
    with open(infile, 'rb') as inp:
        if inp.read(4) != MAGIC:
            raise ValueError(f"Not a {MAGIC.decode()} file or invalid magic number")
        
        num_rows = struct.unpack('<I', inp.read(4))[0]

        if num_rows == 0:
            with open(outfile, 'w') as out:
                pass 
            return

        line_lengths = []
        length_flag = inp.read(1)
        if length_flag == FLAG_UNIFORM_LINE_LENGTHS:
            common_length = read_varint(inp)
            line_lengths = [common_length] * num_rows
        elif length_flag == FLAG_VARIABLE_LINE_LENGTHS:
            for _ in range(num_rows):
                line_lengths.append(read_varint(inp))
        else:
            raise ValueError("Invalid line length flag in compressed file")
        
        actual_total_values = sum(line_lengths)
        reconstructed_vals_2d = []

        if actual_total_values == 0:
            with open(outfile, 'w') as out:
                for _ in range(num_rows):
                    out.write('\n')
            return

        h0 = zigzag_decode(read_varint(inp))
        
        decoded_deltas = []
        num_deltas_to_read = actual_total_values - 1

        if num_deltas_to_read > 0:
            compressed_deltas_payload = inp.read()
            if not compressed_deltas_payload:
                 raise ValueError("Expected delta payload but found none.")
            
            raw_deltas_payload = lzma.decompress(compressed_deltas_payload)
            deltas_stream = BytesIO(raw_deltas_payload)
            for _ in range(num_deltas_to_read):
                try:
                    decoded_deltas.append(zigzag_decode(read_varint(deltas_stream)))
                except EOFError:
                    raise ValueError("Delta stream ended prematurely while reading expected deltas.")
            if deltas_stream.read(1): # Check if there's any data left in the stream
                 raise ValueError("More data in delta stream than expected.")
            if len(decoded_deltas) != num_deltas_to_read: # Should be redundant if EOFError and extra data check are robust
                 raise ValueError(f"Read {len(decoded_deltas)} deltas, expected {num_deltas_to_read}.")

        delta_idx = 0
        for r in range(num_rows):
            current_reconstructed_row = []
            prev_full_row_for_pred = reconstructed_vals_2d[r-1] if r > 0 else None
            current_row_length = line_lengths[r]

            if current_row_length == 0:
                reconstructed_vals_2d.append(current_reconstructed_row)
                continue

            for c in range(current_row_length):
                if r == 0 and c == 0:
                    current_reconstructed_row.append(h0)
                    continue

                val_A = current_reconstructed_row[c-1] if c > 0 else None
                val_B = None
                if prev_full_row_for_pred and c < len(prev_full_row_for_pred):
                    val_B = prev_full_row_for_pred[c]
                
                val_C = None
                if prev_full_row_for_pred and c > 0 and (c-1) < len(prev_full_row_for_pred):
                    val_C = prev_full_row_for_pred[c-1]

                pred = 0
                if val_A is not None and val_B is not None and val_C is not None:
                    pred = paeth_predict(val_A, val_B, val_C)
                elif val_A is not None:
                    pred = val_A
                elif val_B is not None:
                    pred = val_B
                
                if delta_idx >= len(decoded_deltas):
                    raise ValueError(f"Not enough deltas to reconstruct value at row {r}, col {c}.")

                delta = decoded_deltas[delta_idx]
                delta_idx += 1
                
                value = pred + delta
                current_reconstructed_row.append(value)
            
            reconstructed_vals_2d.append(current_reconstructed_row)

    with open(outfile, 'w') as out:
        for i, row_data in enumerate(reconstructed_vals_2d):
            out.write(' '.join(str(x) for x in row_data))
            out.write('\n')


def verify_compression(original_infile: str, compressed_file_to_test: str) -> None:
    fd, tmp_decompressed_name = tempfile.mkstemp(suffix=".txt", text=True)
    os.close(fd) 

    try:
        print(f"Verifying: Decompressing {compressed_file_to_test} to {tmp_decompressed_name}")
        decompress_file(compressed_file_to_test, tmp_decompressed_name)
        
        match = True
        line_num = 0
        with open(original_infile, 'r') as f1, open(tmp_decompressed_name, 'r') as f2:
            while True:
                line_num += 1
                line1 = f1.readline()
                line2 = f2.readline()
                s_line1 = line1.rstrip('\r\n').rstrip() 
                s_line2 = line2.rstrip('\r\n').rstrip()

                if s_line1 == "" and line1 != "" and s_line2 == "" and line2 != "": 
                    pass 
                elif s_line1 != s_line2:
                    print(f"❌ Mismatch detected at line {line_num}:")
                    # To help debug, show how the compressor would parse line1
                    original_line1_parts = []
                    if line1.strip():
                        try:
                            original_line1_parts = line1.strip().split()
                        except: pass # ignore errors for this debug print
                    
                    normalized_s_line1 = ' '.join(original_line1_parts)

                    print(f"Original    : '{s_line1}' (raw: {repr(line1)}) (normalized content: '{normalized_s_line1}')")
                    print(f"Decompressed: '{s_line2}' (raw: {repr(line2)})")
                    match = False
                    break
                
                if not line1 and not line2: 
                    break
                if not line1: 
                    print(f"❌ Mismatch: Original file ended, but decompressed has more data (line {line_num}): '{s_line2}'")
                    match = False
                    break
                if not line2: 
                    print(f"❌ Mismatch: Decompressed file ended, but original has more data (line {line_num}): '{s_line1}'")
                    match = False
                    break
        
        if match:
            print("✔️ Verificación: los archivos coinciden")
        else:
            print("❌ Verificación: ¡ERROR, los archivos difieren!")
            
    except Exception as e:
        print(f"❌ Verificación: ERROR durante la verificación - {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(tmp_decompressed_name):
            os.unlink(tmp_decompressed_name)


def main():
    args = sys.argv[1:]
    verify_flag = False
    if '--verify' in args:
        verify_flag = True
        args.remove('--verify')

    if len(args) != 2:
        print("Usage: python3 script_name.py infile outfile [--verify]")
        print("       python3 script_name.py compressed_file outfile_decompressed")
        sys.exit(1)
    
    infile, outfile_target = args

    start_time = time.time()
    
    is_compression_mode = True 
    try:
        with open(infile, 'rb') as f_peek:
            peek_magic = f_peek.read(len(MAGIC))
        if peek_magic == MAGIC:
            is_compression_mode = False
    except FileNotFoundError:
        print(f"Error: Input file {infile} not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file {infile}: {e}")
        sys.exit(1)

    if not is_compression_mode:
        print(f"-> Modo descompresión (detectado {MAGIC.decode()} en {infile} -> {outfile_target})")
        decompress_file(infile, outfile_target)
    else:
        print(f"-> Modo compresión ({infile} -> {outfile_target})")
        compress_file(infile, outfile_target)
        if verify_flag:
            print("--- Iniciando verificación ---")
            verify_compression(infile, outfile_target) 
            print("--- Verificación finalizada ---")
            
    end_time = time.time()

    size_in = 0
    if os.path.exists(infile):
        size_in = os.path.getsize(infile)
    
    size_out = 0
    if os.path.exists(outfile_target):
        size_out = os.path.getsize(outfile_target)
    
    elapsed = end_time - start_time
    
    speed = 0
    if elapsed > 0 and size_in > 0 :
        speed = (size_in / 1024) / elapsed 

    print(f"- Tiempo: {elapsed:.3f} s")
    print(f"- Tamaño entrada: {size_in/1024:.2f} kB")

    if os.path.exists(outfile_target):
        print(f"- Tamaño salida: {size_out/1024:.2f} kB")
        if is_compression_mode:
            if size_out > 0:
                print(f"- Ratio de compresión: {size_in/size_out:.2f}x")
            elif size_in == 0 : # Input was 0 bytes, output likely 0 or very small (header for 0 rows)
                 print("- Ratio de compresión: N/A (entrada vacía)")
            else: # Output is 0 bytes from a non-empty input (should not happen with current logic)
                print("- Ratio de compresión: N/A (salida vacía, error?)")
    else:
        # This implies an error if outfile_target was expected to be created
        print(f"- Tamaño salida: N/A (fichero no creado, posible error en {'compresión' if is_compression_mode else 'descompresión'})")


    if speed > 0:
        if is_compression_mode:
            print(f"- Velocidad: {speed:.2f} kB/s (basado en tamaño de entrada original)")
        else: 
            print(f"- Velocidad: {speed:.2f} kB/s (basado en tamaño de entrada comprimido)")
    else:
        print(f"- Velocidad: N/A")

if __name__ == '__main__':
    main()