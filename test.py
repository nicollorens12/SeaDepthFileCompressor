import time
import os
from Compressor import GolombRiceCompressor
from FileChecker import FileChecker
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress and decompress a file using Golomb-Rice coding.")

    parser.add_argument('--inputfile', required=True, help="Path to the file to check.")
    parser.add_argument('--outputrawfile', required=False, help="Path to the output raw file.")
    parser.add_argument('--outputfile', required=False, help="Path to the output decoded file.")
    args = parser.parse_args()

    # Arg Checks

    if args.inputfile:
        orig_path    = args.inputfile
    if args.outputrawfile:
        comp_path    = args.outputrawfile
    else :
        comp_path    = 'files/out.bin'
    if args.outputfile:
        reco_path    = args.outputfile
    else :
        reco_path    = 'files/recovered.txt'
 

    comp = GolombRiceCompressor()

    # --- Medir compresión ---
    start_c = time.time()
    comp.compress_file(orig_path, comp_path)
    end_c   = time.time()

    # --- Medir descompresión ---
    start_d = time.time()
    comp.decompress_file(comp_path, reco_path)
    end_d   = time.time()

    # Tamaños
    size_orig = os.path.getsize(orig_path)
    size_comp = os.path.getsize(comp_path)

    # Cálculo de velocidades en kB/s
    rate_c = (size_orig / 1024) / (end_c - start_c)
    rate_d = (size_comp / 1024) / (end_d - start_d)

    # Resultado
    print("Compression and decompression completed successfully.")
    print(f"Original size:   {size_orig/1024:.2f} kB")
    print(f"Compressed size: {size_comp/1024:.2f} kB")
    print(f"  -> Compression rate:   {rate_c:.2f} kB/s")
    print(f"  -> Decompression rate: {rate_d:.2f} kB/s")
    print(f"  -> Compression ratio:   {size_orig/size_comp:.2f}x")

    if rate_c >= 250 and rate_d >= 250:
        print("✅ Both rates exceed 250 kB/s requirement.")
    else:
        print("⚠️ One or both rates are below 250 kB/s!")

    # --- Verificar integridad ---
    checker = FileChecker()
    checker.compare_files(orig_path, reco_path)
