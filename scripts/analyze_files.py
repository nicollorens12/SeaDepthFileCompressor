#!/usr/bin/env python3
import sys
import math
from collections import Counter

# (Copiamos las funciones Paeth del compresor para usarlas aquí)
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

def analyze_file(filepath: str):
    print(f"--- Analizando Archivo: {filepath} ---")

    data_rows = []
    raw_values = []
    line_lengths = []

    try:
        with open(filepath, 'r') as f:
            for line in f:
                stripped_line = line.strip()
                nums_in_line = []
                if stripped_line:
                    try:
                        nums_in_line = [int(x) for x in stripped_line.split()]
                    except ValueError:
                        print(f"Advertencia: Línea con datos no enteros omitida del análisis numérico: '{stripped_line}'")
                data_rows.append(nums_in_line)
                raw_values.extend(nums_in_line)
                line_lengths.append(len(nums_in_line))
    except FileNotFoundError:
        print(f"Error: Archivo no encontrado '{filepath}'")
        return
    except Exception as e:
        print(f"Error leyendo el archivo '{filepath}': {e}")
        return

    if not raw_values:
        print("El archivo no contiene valores numéricos para analizar.")
        if line_lengths:
            print("\n--- Estadísticas de Longitud de Línea ---")
            print(f"Número total de líneas: {len(line_lengths)}")
            if line_lengths:
                print(f"  Mínima longitud de línea: {min(line_lengths)}")
                print(f"  Máxima longitud de línea: {max(line_lengths)}")
                print(f"  Media de longitud de línea: {sum(line_lengths) / len(line_lengths):.2f}")
            line_lengths_counts = Counter(line_lengths)
            print("  Distribución de longitudes de línea (longitud: cantidad):")
            for length, count in sorted(line_lengths_counts.items()):
                print(f"    {length}: {count}")
        return

    # --- Estadísticas de Valores Originales ---
    print("\n--- Estadísticas de Valores Originales ---")
    print(f"Total de valores numéricos: {len(raw_values)}")
    min_val = min(raw_values)
    max_val = max(raw_values)
    mean_val = sum(raw_values) / len(raw_values)
    raw_values_sorted = sorted(raw_values)
    median_val = raw_values_sorted[len(raw_values_sorted) // 2]
    print(f"  Mínimo: {min_val}")
    print(f"  Máximo: {max_val}")
    print(f"  Media: {mean_val:.2f}")
    print(f"  Mediana: {median_val}")

    # Histograma simple para valores originales
    print("  Distribución de Valores Originales (Histograma simple):")
    num_bins = 10
    if max_val == min_val: # Avoid division by zero if all values are the same
        print(f"    Todos los valores son: {min_val}")
    else:
        bin_size = (max_val - min_val) / num_bins
        if bin_size == 0: bin_size = 1 # case where max_val is very close to min_val

        bins = [0] * num_bins
        for val in raw_values:
            bin_index = min(int((val - min_val) / bin_size), num_bins - 1) if bin_size > 0 else 0
            bins[bin_index] += 1
        
        for i in range(num_bins):
            bin_start = min_val + i * bin_size
            bin_end = min_val + (i + 1) * bin_size
            print(f"    Rango [{bin_start:.2f} - {bin_end:.2f}): {bins[i]} valores")


    # --- Estadísticas de Longitud de Línea ---
    print("\n--- Estadísticas de Longitud de Línea ---")
    print(f"Número total de líneas: {len(line_lengths)}")
    if line_lengths: # Check if line_lengths is not empty
        print(f"  Mínima longitud de línea: {min(line_lengths)}")
        print(f"  Máxima longitud de línea: {max(line_lengths)}")
        print(f"  Media de longitud de línea: {sum(line_lengths) / len(line_lengths):.2f}")
    line_lengths_counts = Counter(line_lengths)
    print("  Distribución de longitudes de línea (longitud: cantidad):")
    for length, count in sorted(line_lengths_counts.items()):
        print(f"    {length}: {count}")


    # --- Cálculo y Estadísticas de Deltas (con Paeth) ---
    print("\n--- Estadísticas de Deltas (Predicción Paeth) ---")
    if len(raw_values) <= 1:
        print("No hay suficientes datos para calcular deltas.")
    else:
        deltas = []
        reconstructed_rows_for_pred = [] # Similar to compressor

        # h0 is the first value, not a delta
        # The deltas start from the second value in _vals_flat
        
        first_val_processed = False
        for r, current_actual_row_values in enumerate(data_rows):
            current_processing_row_for_reconstruction = []
            prev_reconstructed_full_row = reconstructed_rows_for_pred[r-1] if r > 0 else None

            for c, actual_val in enumerate(current_actual_row_values):
                if not first_val_processed:
                    current_processing_row_for_reconstruction.append(actual_val)
                    first_val_processed = True # This is h0, skip delta calculation for it
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
                deltas.append(delta)
                current_processing_row_for_reconstruction.append(actual_val)
            
            reconstructed_rows_for_pred.append(current_processing_row_for_reconstruction)

        if not deltas:
            print("No se generaron deltas (quizás solo hay un valor numérico).")
        else:
            print(f"Total de deltas generados: {len(deltas)}")
            min_delta = min(deltas)
            max_delta = max(deltas)
            mean_delta = sum(deltas) / len(deltas)
            deltas_sorted = sorted(deltas)
            median_delta = deltas_sorted[len(deltas_sorted) // 2]
            zeros_count = deltas.count(0)
            percentage_zeros = (zeros_count / len(deltas)) * 100 if len(deltas) > 0 else 0

            print(f"  Mínimo delta: {min_delta}")
            print(f"  Máximo delta: {max_delta}")
            print(f"  Media delta: {mean_delta:.2f}")
            print(f"  Mediana delta: {median_delta}")
            print(f"  Cantidad de deltas = 0: {zeros_count} ({percentage_zeros:.2f}%)")

            # Histograma simple para deltas
            print("  Distribución de Deltas (Histograma simple):")
            num_delta_bins = 20 # More bins for deltas as they are often clustered around 0
            
            # Filter out extreme outliers for histogram display if necessary, or use a wider range
            # For simplicity, we'll use min/max of actual deltas
            if max_delta == min_delta:
                 print(f"    Todos los deltas son: {min_delta}")
            else:
                delta_bin_size = (max_delta - min_delta) / num_delta_bins
                if delta_bin_size == 0: delta_bin_size = 1

                delta_bins = [0] * num_delta_bins
                for d_val in deltas:
                    bin_index = min(int((d_val - min_delta) / delta_bin_size), num_delta_bins - 1) if delta_bin_size > 0 else 0
                    delta_bins[bin_index] += 1

                for i in range(num_delta_bins):
                    bin_start = min_delta + i * delta_bin_size
                    bin_end = min_delta + (i + 1) * delta_bin_size
                    print(f"    Rango [{bin_start:.2f} - {bin_end:.2f}): {delta_bins[i]} deltas")
            
            # Top N most common deltas
            delta_counts = Counter(deltas)
            print("  Top 10 deltas más comunes (delta: cantidad):")
            for delta_val, count in delta_counts.most_common(10):
                print(f"    {delta_val}: {count}")

    print(f"--- Fin del Análisis: {filepath} ---")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 analyze_data.py <ruta_al_fichero_de_datos_1> [ruta_al_fichero_de_datos_2 ...]")
        sys.exit(1)
    
    for filepath_arg in sys.argv[1:]:
        analyze_file(filepath_arg)
        print("\n" + "="*70 + "\n") # Separator for multiple files