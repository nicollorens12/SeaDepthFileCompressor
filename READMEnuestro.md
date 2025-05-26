# PracticaCDI

## Descripcion de archivos

### Carpetas

- `/files/` - Carpeta que contiene los archivos de entrada y salida, vacia por defecto por tamaño

### Clases
- `Compressor.py` - Archivo que contiene la clase `GolombRiceCompressor`, que se encarga de comprimir de formato entrada a .bin y descomprimir de .bin a formato entrada.

- `FileChecker.py` - Archivo que contiene la clase `FileChecker`, que se encarga de verificar si los archivos de entrada y salida son iguales.

- `InputFileGenerator.py` - Archivo que contiene la clase `InputFileGenerator`, que se encarga de generar archivos de entrada aleatorios con el formato de entrada.

### Scripts

- `test.py`: Script que dado un archivo como argumento de entrada, lo comprime, lo descomprime y verifica si el archivo de salida es igual al archivo de entrada. 

- `generate_files.py`: Script que genera archivos de entrada de diferentes formas con el formato de entrada. 

- `original_file_checker.py`: Script que analiza la forma de los archivos de entrada, usada para entender como se deberan generar los archivos de entrada sintentico desde la clase `InputFileGenerator`.


## Observaciones Archivos de Ejemplo Originales

- Tienen 849 filas
- Tienen 35001 cotas por fila

## Compresion actual:

### file11111.txt
Original size:   165083.86 kB
Compressed size: 28861.74 kB
  - Compression rate:   4307.52 kB/s
  - Decompression rate: 938.90 kB/s
  - Compression ratio:   5.72x

✅ Both rates exceed 250 kB/s requirement.

### file22222.txt
Original size:   176167.14 kB
Compressed size: 21489.81 kB
  - Compression rate:   5556.31 kB/s
  - Decompression rate: 858.53 kB/s
  - Compression ratio:   8.20x

✅ Both rates exceed 250 kB/s requirement.

## Compresion test:
### file11111.txt
Original size:   165083.86 kB
Compressed size: 27927.89 kB
  - Compression rate:   4204.85 kB/s
  - Decompression rate: 923.87 kB/s
  - Compression ratio:   5.91x

✅ Both rates exceed 250 kB/s requirement.

### file22222.txt
Original size:   176167.14 kB
Compressed size: 21489.81 kB
  - Compression rate:   5466.34 kB/s
  - Decompression rate: 881.81 kB/s
  - Compression ratio:   8.20x

✅ Both rates exceed 250 kB/s requirement.


## Compresion test Huffam
### file11111.txt
Compression and decompression completed successfully.
Original size:   165083.86 kB
Compressed size: 26121.39 kB
  - Compression rate:   2315.17 kB/s
  - Decompression rate: 494.15 kB/s
  - Compression ratio:   6.32x

✅ Both rates exceed 250 kB/s requirement.
The files 'files/file11111.txt' and 'files/recovered.txt' are identical.

### file22222.txt
Compression and decompression completed successfully.
Original size:   176167.14 kB
Compressed size: 19684.78 kB
  - Compression rate:   3054.77 kB/s
  - Decompression rate: 458.33 kB/s
  - Compression ratio:   8.95x
  
✅ Both rates exceed 250 kB/s requirement.
The files 'files/file22222.txt' and 'files/recovered.txt' are identical.

## Compresion second-order deltas + ZigZag + Elias-gamma coding + canonical Huffman

Media de compression ratio: (7,7 + 8,33 + 7,73 + 8,43 ) / 4 = 8,04x

### file11111.txt
Compression and decompression completed successfully.
Original size:   165083.86 kB
Compressed size: 21433.07 kB
  - Compression rate:   4208.15 kB/s
  - Decompression rate: 498.48 kB/s
  - Compression ratio:   7.70x

✅ Both rates exceed 250 kB/s requirement.
The files 'files/file11111.txt' and 'files/recovered.txt' are identical.

### file22222.txt
Compression and decompression completed successfully.
Original size:   176167.14 kB
Compressed size: 21141.94 kB
  - Compression rate:   4521.32 kB/s
  - Decompression rate: 477.60 kB/s
  - Compression ratio:   8.33x

✅ Both rates exceed 250 kB/s requirement.
The files 'files/file22222.txt' and 'files/recovered.txt' are identical.

### file21212.txt
Compression and decompression completed successfully.
Original size:   176167.14 kB
Compressed size: 22792.16 kB
  - Compression rate:   5737.59 kB/s
  - Decompression rate: 608.56 kB/s
  - Compression ratio:   7.73x
✅ Both rates exceed 250 kB/s requirement.
The files 'files/file21212.txt' and 'files/recoveredold.txt' are identical.✅

### file22121.txt

Compression and decompression completed successfully.
Original size:   176372.23 kB
Compressed size: 20912.29 kB
  - Compression rate:   5940.14 kB/s
  - Decompression rate: 608.58 kB/s
  - Compression ratio:   8.43x
✅ Both rates exceed 250 kB/s requirement.
The files 'files/file22121.txt' and 'files/recoveredold.txt' are identical.✅

## Compresion Improved

Media de compression ratio: (8,25 + 8,22 + 8,48 + 9,16 ) / 4 = 8.53x

### file11111.txt
Compression and decompression completed successfully.
Original size:   165083.86 kB
Compressed size: 20007.52 kB
  - Compression rate:   5694.34 kB/s
  - Decompression rate: 696.00 kB/s
  - Compression ratio:   8.25x
✅ Both rates exceed 250 kB/s requirement.
The files 'files/file11111.txt' and 'files/recovered.txt' are identical.✅

### file22222.txt
Compression and decompression completed successfully.
Original size:   176167.14 kB
Compressed size: 21433.07 kB
  - Compression rate:   5658.37 kB/s
  - Decompression rate: 737.86 kB/s
  - Compression ratio:   8.22x
✅ Both rates exceed 250 kB/s requirement.
The files 'files/file22222.txt' and 'files/recovered.txt' are identical.✅

### file21212.txt
Compression and decompression completed successfully.
Original size:   176167.14 kB
Compressed size: 20785.29 kB
  - Compression rate:   5659.98 kB/s
  - Decompression rate: 700.24 kB/s
  - Compression ratio:   8.48x
✅ Both rates exceed 250 kB/s requirement.
The files 'files/file21212.txt' and 'files/recovered.txt' are identical.✅

### file22121.txt

Compression and decompression completed successfully.
Original size:   176372.23 kB
Compressed size: 19260.78 kB
  - Compression rate:   5906.61 kB/s
  - Decompression rate: 656.63 kB/s
  - Compression ratio:   9.16x
✅ Both rates exceed 250 kB/s requirement.
The files 'files/file22121.txt' and 'files/recovered.txt' are identical.✅

