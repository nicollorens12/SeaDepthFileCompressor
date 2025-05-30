# BPR5: Lossless compression for sea level height data

[![es](https://img.shields.io/badge/language-es-yellow.svg)](README.md)

The script `compress.py` implements a lossless compression pipeline specifically designed to compress sequences of sea level height data (available in the `files/` directory).

The pipeline consists of block-wise preprocessing (row-wise prediction + delta encoding), ZigZag transformation, variable-length encoding (varint), and final compression using LZMA.

The `report.pdf` document describes the process in more detail.

> This project was developed as part of the "Data and Image Compression" course (CDI) at FIB-UPC, during the Spring semester of the 2024–2025 academic year. Developed by Sol Torralba, Fernando Guirao, and Nico Llorens.

## Requirements

We worked with Python version 3.13, but no packages outside the standard library are required.

## Usage

To compress a file:

```bash
python3 compress.py input_file.txt output_file.bin
````

To decompress:

```bash
python3 compress.py compressed_file.bin output_file.txt
```

To verify that compression and decompression are lossless:

```bash
python3 compress.py input_file.txt output_file.bin --verify
```

The script automatically detects whether the input file is compressed.

## Compression ratios obtained

| File          | Compression Ratio |
| ------------- | ----------------- |
| file11111.txt | 8.44x             |
| file22222.txt | 10.18x            |
| file21212.txt | 9.12x             |
| file22121.txt | 10.25x            |