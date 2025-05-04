# Compresor sin pérdidas — PracticaCDI (lab_33)

Este script `compress.py` permite **comprimir** y **descomprimir** archivos de texto con datos de alturas sobre el nivel del mar.

## Uso

```bash
python3 compress.py infile outfile
````

* Si `infile` termina en `.txt`, se asume que es un archivo original → **se comprime** a `outfile` (por ejemplo, `.bin`).
* Si `infile` termina en `.bin`, se asume que es un archivo comprimido → **se descomprime** a `outfile` (por ejemplo, `.txt`).

## Ejemplos

```bash
# Comprimir
python3 compress.py files/file11111.txt files/compressed.bin

# Descomprimir
python3 compress.py files/compressed.bin files/recovered.txt
```

## Salida por terminal

El script imprime al ejecutarse:

* Modo seleccionado (compresión o descompresión).
* Tiempo de ejecución.
* Tamaños de entrada y salida.
* **Ratio de compresión** (solo en modo compresión).
* **Velocidad de procesamiento** en kB/s.

### Ejemplo de salida en compresión:

```
-> Modo compresión
- Compresión completada en 34.64 s
- Tamaño original:   165083.86 kB
- Tamaño comprimido: 21433.07 kB
- Ratio de compresión: 7.70x
- Velocidad: 4765.07 kB/s
```

### Ejemplo de salida en descompresión:

```
-> Modo descompresión
- Descompresión completada en 39.92 s
- Tamaño comprimido: 21433.07 kB
- Tamaño recuperado: 165083.86 kB
- Velocidad: 536.88 kB/s
```

## Requisitos

* Python 3 (probado en entorno Linux FIB).
* No se necesitan librerías externas.
