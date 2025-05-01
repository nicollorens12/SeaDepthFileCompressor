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
Compressed size: 26471.17 kB
  - Compression rate:   4191.21 kB/s
  - Decompression rate: 863.80 kB/s
  - Compression ratio:   6.24x

✅ Both rates exceed 250 kB/s requirement.

✅ The files '.\files\file11111.txt' and 'files/recovered.txt' are identical.

### file22222.txt
Original size:   176167.14 kB
Compressed size: 21357.74 kB
  - Compression rate:   4989.64 kB/s
  - Decompression rate: 719.20 kB/s
  - Compression ratio:   8.25x

✅ Both rates exceed 250 kB/s requirement.

✅ The files '.\files\file22222.txt' and 'files/recovered.txt' are identical.