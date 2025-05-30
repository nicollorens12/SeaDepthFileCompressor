import sys

P_LEFT, P_UP, P_PAETH, P_MED = 0, 1, 2, 3
PREDICTORS = [P_LEFT, P_UP, P_PAETH, P_MED]
PRED_NAMES = {0: "LEFT", 1: "UP", 2: "PAETH", 3: "MED"}

def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc: return a
    if pb <= pc: return b
    return c

def med(a, b, c):
    if c >= max(a, b): return min(a, b)
    elif c <= min(a, b): return max(a, b)
    else: return a + b - c

def predict(i, j, row, prev_row, pid):
    a = row[j-1] if j > 0 else 0
    b = prev_row[j] if prev_row and j < len(prev_row) else 0
    c = prev_row[j-1] if prev_row and j > 0 else 0
    if pid == P_LEFT: return a
    elif pid == P_UP: return b
    elif pid == P_PAETH: return paeth(a, b, c)
    elif pid == P_MED: return med(a, b, c)
    else: return 0

def error_predictor_rowwise(data):
    total_error = 0
    best_pids = []
    prev_row = None
    for i, row in enumerate(data):
        best_error = float('inf')
        best_pid = None
        for pid in PREDICTORS:
            error = 0
            for j, v in enumerate(row):
                if prev_row is None and j == 0: continue
                pred = predict(i, j, row, prev_row, pid)
                error += abs(v - pred)
            if error < best_error:
                best_error = error
                best_pid = pid
        best_pids.append(best_pid)
        total_error += best_error
        prev_row = row
    return total_error, best_pids

def error_predictor_colwise(data):
    num_cols = max(len(row) for row in data)
    total_error = 0
    best_pids = []
    for j in range(num_cols):
        col_vals = [row[j] if j < len(row) else 0 for row in data]
        best_error = float('inf')
        best_pid = None
        for pid in PREDICTORS:
            error = 0
            for i in range(len(data)):
                a = col_vals[i-1] if i > 0 else 0
                b = col_vals[i-1] if i > 0 else 0
                c = col_vals[i-2] if i > 1 else 0
                if pid == P_LEFT: pred = a
                elif pid == P_UP: pred = b
                elif pid == P_PAETH: pred = paeth(a, b, c)
                elif pid == P_MED: pred = med(a, b, c)
                else: pred = 0
                if i > 0:
                    error += abs(col_vals[i] - pred)
            if error < best_error:
                best_error = error
                best_pid = pid
        best_pids.append(best_pid)
        total_error += best_error
    return total_error, best_pids

def main(fname):
    with open(fname) as f:
        data = [list(map(int, line.strip().split())) for line in f if line.strip()]
    err_row, pids_row = error_predictor_rowwise(data)
    err_col, pids_col = error_predictor_colwise(data)

    print(f"Error total por filas:     {err_row}")
    print(f"Error total por columnas: {err_col}")
    print("\nResultado:")
    if err_row < err_col:
        print("✅ Mejor usar predicción por FILAS")
    elif err_col < err_row:
        print("✅ Mejor usar predicción por COLUMNAS")
    else:
        print("⚖️  Ambas estrategias tienen el mismo error")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 analiza_predictores.py archivo.txt")
    else:
        main(sys.argv[1])
