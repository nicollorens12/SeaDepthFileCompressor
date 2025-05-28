#!/usr/bin/env python3
import struct
import math
import sys
import os
import time
import lzma
import tempfile
from io import BytesIO # Added for BytesIO in decompress

# Magic header for our 2D Paeth LZMA-based compressor
MAGIC = b'P2DL' # Changed Magic to reflect new method

# Varint encoding/decoding functions (unchanged)
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

# Zigzag functions (unchanged)
def zigzag_encode(n: int) -> int:
    return (n << 1) ^ (n >> 31)

def zigzag_decode(z: int) -> int:
    return (z >> 1) ^ -(z & 1)

# Paeth Predictor
def paeth_predict(a: int, b: int, c: int) -> int:
    # a = left, b = up, c = upper-left
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

# Compressor using 2D Paeth prediction, Varint-coded deltas, and LZMA
def compress_file(infile: str, outfile: str) -> None:
    data_rows = []
    with open(infile, 'r') as f:
        for line in f:
            # Skip empty lines that might result from multiple newlines
            stripped_line = line.strip()
            if not stripped_line:
                # Decide policy: if a file can have "empty rows" that are significant,
                # this needs to be handled (e.g., store as zero-length rows).
                # For now, skipping lines that are purely whitespace.
                continue
            nums = [int(x) for x in stripped_line.split()]
            data_rows.append(nums)

    # Flatten data_rows to get all values for total count and h0
    _vals_flat = [val for row in data_rows for val in row]

    if not _vals_flat:
        # This will handle truly empty files or files that became empty after stripping lines.
        # To create an empty compressed file:
        with open(outfile, 'wb') as out:
            out.write(MAGIC)
            out.write(struct.pack('<I', 0)) # total_num_values = 0
            # No h0, num_rows, line_lengths, or data for empty file
        return

    h0 = _vals_flat[0]
    total_num_values = len(_vals_flat)
    num_rows = len(data_rows)
    line_lengths = [len(row) for row in data_rows]

    deltas_to_encode = []
    # This list will hold the reconstructed values, row by row, to be used by the predictor
    reconstructed_rows_for_pred = []

    for r, current_actual_row_values in enumerate(data_rows):
        current_processing_row_for_reconstruction = []
        prev_reconstructed_full_row = reconstructed_rows_for_pred[r-1] if r > 0 else None

        for c, actual_val in enumerate(current_actual_row_values):
            if r == 0 and c == 0:
                current_processing_row_for_reconstruction.append(actual_val) # This is h0
                continue # h0 is stored raw, no delta for it

            # Predictor values: A (left), B (up), C (up-left)
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
            elif val_A is not None: # Only left available (e.g., top row after first element)
                pred = val_A
            elif val_B is not None: # Only up available (e.g., first column after first row)
                pred = val_B
            # Else, if none are available (should not happen after h0), pred remains 0

            delta = actual_val - pred
            deltas_to_encode.append(delta)
            current_processing_row_for_reconstruction.append(actual_val)
        
        reconstructed_rows_for_pred.append(current_processing_row_for_reconstruction)

    raw_deltas_payload = bytearray()
    for d_val in deltas_to_encode:
        raw_deltas_payload.extend(write_varint(zigzag_encode(d_val)))

    compressed_deltas = lzma.compress(bytes(raw_deltas_payload), preset=9)

    with open(outfile, 'wb') as out:
        out.write(MAGIC)
        out.write(struct.pack('<I', total_num_values))
        if total_num_values > 0: # Only write h0 if there are values
            out.write(struct.pack('<i', h0))
        out.write(struct.pack('<I', num_rows))
        for length in line_lengths:
            out.write(write_varint(length))
        out.write(compressed_deltas)


def decompress_file(infile: str, outfile: str) -> None:
    with open(infile, 'rb') as inp:
        if inp.read(4) != MAGIC:
            raise ValueError(f"Not a {MAGIC.decode()} file or invalid magic number")
        
        total_num_values = struct.unpack('<I', inp.read(4))[0]

        if total_num_values == 0: # Handle empty compressed file
            with open(outfile, 'w') as out: # Create an empty text file
                pass
            return

        h0 = struct.unpack('<i', inp.read(4))[0]
        num_rows = struct.unpack('<I', inp.read(4))[0]
        
        line_lengths = []
        for _ in range(num_rows):
            line_lengths.append(read_varint(inp))
        
        compressed_deltas = inp.read()

    raw_deltas_payload = lzma.decompress(compressed_deltas)
    
    deltas_stream = BytesIO(raw_deltas_payload)
    decoded_deltas = []
    # Number of deltas is total_num_values - 1 (if total_num_values > 0)
    num_deltas_to_read = total_num_values - 1
    for _ in range(num_deltas_to_read):
        decoded_deltas.append(zigzag_decode(read_varint(deltas_stream)))

    reconstructed_vals_2d = []
    delta_idx = 0

    for r in range(num_rows):
        current_reconstructed_row = []
        # Previous fully reconstructed row for predictor
        prev_full_row_for_pred = reconstructed_vals_2d[r-1] if r > 0 else None
        
        current_row_length = line_lengths[r]
        if current_row_length == 0 and r < num_rows -1 : # Handle empty rows if they were stored
             reconstructed_vals_2d.append(current_reconstructed_row)
             continue
        if current_row_length == 0 and r == num_rows -1 and total_num_values > sum(len(x) for x in reconstructed_vals_2d) :
            # This case is tricky, if last line_length is 0 but there are still values expected.
            # For now, assuming line_lengths correctly represent all values.
            pass


        for c in range(current_row_length):
            if r == 0 and c == 0:
                current_reconstructed_row.append(h0)
                continue

            # Predictor values: A (left), B (up), C (up-left)
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
            # Else pred remains 0

            if delta_idx >= len(decoded_deltas):
                # This can happen if line_lengths sum up to more than total_num_values - 1 deltas
                # Or if total_num_values was 1, decoded_deltas is empty
                raise ValueError("Mismatch between expected values and available deltas.")

            delta = decoded_deltas[delta_idx]
            delta_idx += 1
            
            value = pred + delta
            current_reconstructed_row.append(value)
        
        reconstructed_vals_2d.append(current_reconstructed_row)

    with open(outfile, 'w') as out:
        for row_data in reconstructed_vals_2d:
            out.write(' '.join(str(x) for x in row_data) + '\n')


def verify_compression(infile: str, compressed_file: str) -> None: # Renamed variable
    # Decompress to temporary and compare
    fd, tmp_decompressed_name = tempfile.mkstemp()
    os.close(fd) # close file descriptor, NamedTemporaryFile handles delete better

    try:
        print(f"Verifying: Decompressing {compressed_file} to {tmp_decompressed_name}")
        decompress_file(compressed_file, tmp_decompressed_name)
        
        # For large files, read chunk by chunk or compare line by line
        match = True
        with open(infile, 'r') as f1, open(tmp_decompressed_name, 'r') as f2:
            while True:
                line1 = f1.readline()
                line2 = f2.readline()
                if line1 == "" and line2 == "": # Both EOF
                    break
                if line1.strip() != line2.strip(): # Compare stripped lines to handle potential newline differences if any
                    # Or compare exact lines if format must be identical including trailing spaces/newlines
                    print(f"Mismatch detected:\nOriginal: '{line1.strip()}'\nDecompressed: '{line2.strip()}'")
                    match = False
                    break
        
        if match:
            print("✔️ Verificación: los archivos coinciden")
        else:
            print("❌ Verificación: ¡ERROR, los archivos difieren!")
            # Optionally, print more context or diff
            
    except Exception as e:
        print(f"❌ Verificación: ERROR durante la verificación - {e}")
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
        sys.exit(1)
    infile, outfile = args

    start_time = time.time() # Renamed 'start' to 'start_time'
    
    # Determine mode based on infile's magic number
    # This requires reading a bit of the infile if it might be compressed
    try:
        with open(infile, 'rb') as f_peek:
            peek_magic = f_peek.read(len(MAGIC))
    except Exception as e:
        print(f"Error reading input file {infile}: {e}")
        sys.exit(1)

    if peek_magic == MAGIC:
        print(f"-> Modo descompresión (detectado {MAGIC.decode()} en {infile})")
        decompress_file(infile, outfile)
    else:
        print(f"-> Modo compresión ({infile} -> {outfile})")
        compress_file(infile, outfile)
        if verify_flag:
            print("--- Iniciando verificación ---")
            verify_compression(infile, outfile) # Pass original infile and the newly created outfile
            print("--- Verificación finalizada ---")
            
    end_time = time.time() # Renamed 'end' to 'end_time'

    size_in = os.path.getsize(infile)
    # outfile might not exist if decompression failed early or input was empty for compression
    size_out = 0
    if os.path.exists(outfile):
        size_out = os.path.getsize(outfile)
    
    elapsed = end_time - start_time
    
    # Avoid division by zero for speed if elapsed is too small or size_in is 0
    speed = 0
    if elapsed > 0 and size_in > 0 :
        speed = (size_in / 1024) / elapsed # kB/s based on input size processed

    print(f"- Tiempo: {elapsed:.3f} s")
    print(f"- Tamaño entrada: {size_in/1024:.2f} kB")
    if size_out > 0 : # Only print output size and ratio if output file was created
        print(f"- Tamaño salida: {size_out/1024:.2f} kB")
        if peek_magic != MAGIC and size_out > 0: # Compression mode and output exists
            print(f"- Ratio de compresión: {size_in/size_out:.2f}x")
    else:
        print(f"- Tamaño salida: N/A (posiblemente error o fichero de entrada vacío)")

    if speed > 0:
        print(f"- Velocidad: {speed:.2f} kB/s (basado en tamaño de entrada)")
    else:
        print(f"- Velocidad: N/A")


if __name__ == '__main__':
    main()