# BPR5: Compresión sin pérdidas para datos de alturas sobre el nivel del mar

[![en](https://img.shields.io/badge/language-en-blue.svg)](README.en.md)

El script `compress.py` implementa un pipeline de compresión sin pérdidas específicamente creado para comprimir secuencias de datos de alturas sobre el nivel del mar (disponibles en `files/`).

El pipeline consiste en un preprocesado por bloques (predicción por filas + codificación delta), transformación ZigZag, codificación variable (varint), y compresión final con LZMA.

El documento `report.pdf` describe el proceso con más detalle.

> Este trabajo es parte de la asignatura de Compresión de Datos e Imágenes (CDI) de la FIB-UPC en el cuatrimestre de primavera del curso 2024-2025. Realizado por Sol Torralba, Fernando Guirao y Nico Llorens.

## Requisitos

Hemos trabajado con la versión 3.13 de Python, pero no son necesarios paquetes fuera de la librería estándar.

## Uso

Para comprimir un archivo:

```
python3 compress.py archivo_entrada.txt archivo_salida.bin
```

Para descomprimir:

```
python3 compress.py archivo_comprimido.bin archivo_salida.txt
```

Para verificar que la compresión y descompresión mantienen los datos intactos:

```
python3 compress.py archivo_entrada.txt archivo_salida.bin --verify
```

El script detecta automáticamente si el archivo de entrada está comprimido.

## Ratios de compresión obtenidos

| Fichero            | Ratio de compresión |
|--------------------|---------------------|
| file11111.txt      | 8.44x               |
| file22222.txt      | 10.18x              |
| file21212.txt      | 9.12x               |
| file22121.txt      | 10.25x              |