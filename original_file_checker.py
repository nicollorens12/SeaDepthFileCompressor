def check_line_lengths(file1_path, file2_path):
    """
    Analiza dos archivos y compara el número de elementos por línea.
    
    Args:
        file1_path: Ruta al primer archivo
        file2_path: Ruta al segundo archivo
    
    Returns:
        None, imprime los resultados en consola
    """
    try:
        # Analizar el primer archivo
        with open(file1_path, 'r') as f:
            file1_lines = f.readlines()
            
        file1_lengths = []
        for i, line in enumerate(file1_lines):
            line = line.strip()
            if line:  # Ignorar líneas vacías
                nums = line.split()
                file1_lengths.append(len(nums))
                
        # Analizar el segundo archivo
        with open(file2_path, 'r') as f:
            file2_lines = f.readlines()
            
        file2_lengths = []
        for i, line in enumerate(file2_lines):
            line = line.strip()
            if line:  # Ignorar líneas vacías
                nums = line.split()
                file2_lengths.append(len(nums))
        
        # Mostrar resultados
        print(f"Análisis del archivo: {file1_path}")
        print(f"- Total de líneas: {len(file1_lines)}")
        if file1_lengths:
            print(f"- Números por línea: {file1_lengths[0]} (primera línea)")
            
            # Verificar si todas las líneas tienen la misma longitud
            if len(set(file1_lengths)) == 1:
                print(f"- Todas las líneas tienen {file1_lengths[0]} números")
            else:
                print(f"- Longitudes variables: {sorted(set(file1_lengths))}")
        
        print(f"\nAnálisis del archivo: {file2_path}")
        print(f"- Total de líneas: {len(file2_lines)}")
        if file2_lengths:
            print(f"- Números por línea: {file2_lengths[0]} (primera línea)")
            
            # Verificar si todas las líneas tienen la misma longitud
            if len(set(file2_lengths)) == 1:
                print(f"- Todas las líneas tienen {file2_lengths[0]} números")
            else:
                print(f"- Longitudes variables: {sorted(set(file2_lengths))}")
        
        # Comparar los dos archivos
        if file1_lengths == file2_lengths:
            print("\n✅ Los archivos tienen el mismo patrón de longitud de líneas")
        else:
            print("\n❌ Los archivos tienen diferentes longitudes de línea")
            
            # Mostrar la primera diferencia
            for i, (len1, len2) in enumerate(zip(file1_lengths, file2_lengths)):
                if len1 != len2:
                    print(f"- Primera diferencia en línea {i+1}: {len1} vs {len2}")
                    break
        
    except FileNotFoundError as e:
        print(f"Error: No se pudo encontrar el archivo. {e}")
    except Exception as e:
        print(f"Error al procesar los archivos: {e}")

if __name__ == "__main__":
    file1 = "files/file11111.txt"
    file2 = "files/file22222.txt"
    
    check_line_lengths(file1, file2)