#!/usr/bin/env python3
import sys, os, time, lzma, tempfile
from io import BytesIO

MAGIC = b'BPR5'
BLOCK_SIZE = 8
P_LEFT, P_UP, P_PAETH, P_MED = 0, 1, 2, 3

def write_varint(n:int)->bytes:
    out=bytearray()
    while True:
        b=n&0x7F; n>>=7
        if n: out.append(b|0x80)
        else: out.append(b); break
    return bytes(out)

def read_varint(f)->int:
    shift=0; res=0
    while True:
        b=f.read(1)
        if not b: raise EOFError
        byte=b[0]
        res |= (byte&0x7F)<<shift
        if not (byte&0x80): break
        shift+=7
    return res

def paeth(a,b,c):
    p=a+b-c; pa=abs(p-a); pb=abs(p-b); pc=abs(p-c)
    if pa<=pb and pa<=pc: return a
    if pb<=pc: return b
    return c

def med(a,b,c):
    if c >= max(a, b): return min(a, b)
    elif c <= min(a, b): return max(a, b)
    else: return a + b - c

def zigzag_encode(n:int)->int:
    return (n<<1) ^ (n>>31)

def zigzag_decode(z:int)->int:
    return (z>>1) ^ -(z&1)

def select_predictor_for_row(row, prev_row):
    sums = [0, 0, 0, 0]
    for pid in (P_LEFT, P_UP, P_PAETH, P_MED):
        total = 0
        for i,v in enumerate(row):
            if prev_row is None and i == 0:
                continue
            if pid==P_LEFT:
                pred = row[i-1] if i>0 else 0
            elif pid==P_UP:
                pred = prev_row[i] if prev_row and i<len(prev_row) else 0
            elif pid==P_PAETH:
                a = row[i-1] if i>0 else 0
                b = prev_row[i] if prev_row and i<len(prev_row) else 0
                c = prev_row[i-1] if prev_row and i>0 else 0
                pred = paeth(a,b,c)
            else:
                a = row[i-1] if i>0 else 0
                b = prev_row[i] if prev_row and i<len(prev_row) else 0
                c = prev_row[i-1] if prev_row and i>0 else 0
                pred = med(a,b,c)
            total += abs(v-pred)
        sums[pid]=total
    return min(( (sums[i],i) for i in (P_LEFT,P_UP,P_PAETH,P_MED) ))[1]

def delta1(row, rec, prev, pid):
    deltas = []
    for j, v in enumerate(row):
        if prev is None and j == 0:
            rec.append(v)
            continue
        if pid == P_LEFT:
            pred = rec[j-1] if j > 0 else 0
        elif pid == P_UP:
            pred = prev[j] if prev and j < len(prev) else 0
        elif pid == P_PAETH:
            a = rec[j-1] if j > 0 else 0
            b = prev[j] if prev and j < len(prev) else 0
            c = prev[j-1] if prev and j > 0 else 0
            pred = paeth(a,b,c)
        else:
            a = rec[j-1] if j > 0 else 0
            b = prev[j] if prev and j < len(prev) else 0
            c = prev[j-1] if prev and j > 0 else 0
            pred = med(a,b,c)
        delta = v - pred
        deltas.append(delta)
        rec.append(v)
    return deltas

def delta2(row, rec, prev, pid):
    deltas = []
    for j, v in enumerate(row):
        if j == 0:
            if prev is None:
                rec.append(v)
                continue
            if pid == P_LEFT:
                pred = 0
            elif pid == P_UP:
                pred = prev[j] if prev and j < len(prev) else 0
            elif pid == P_PAETH:
                pred = paeth(0, prev[j] if prev and j < len(prev) else 0, 0)
            else:
                pred = med(0, prev[j] if prev and j < len(prev) else 0, 0)
            val = v
            delta = val - pred
            rec.append(val)
            deltas.append(delta)
        elif j == 1:
            delta = v - rec[j - 1]
            rec.append(v)
            deltas.append(delta)
        else:
            delta = v - 2 * rec[j - 1] + rec[j - 2]
            rec.append(v)
            deltas.append(delta)
    return deltas

def compress_file(infile, outfile):
    rows = [list(map(int, line.split())) for line in open(infile)]
    num_rows = len(rows)

    hdr = bytearray()
    hdr += MAGIC
    hdr += write_varint(num_rows)
    for r in rows:
        hdr += write_varint(len(r))
    flat = [x for r in rows for x in r]
    if not flat:
        open(outfile, 'wb').write(hdr)
        return
    h0 = flat[0]
    hdr += write_varint(zigzag_encode(h0))

    predictor_counts = {P_LEFT: 0, P_UP: 0, P_PAETH: 0, P_MED: 0}
    delta_mode_counts = {0: 0, 1: 0}

    blocks = []
    preds_all = []
    modes_all = []
    prev = None
    for i in range(0, num_rows, BLOCK_SIZE):
        block_rows = rows[i:i+BLOCK_SIZE]
        preds = []
        modes = []
        encoded = bytearray()
        for row in block_rows:
            pid = select_predictor_for_row(row, prev)
            preds.append(pid)
            predictor_counts[pid] += 1

            rec1, rec2 = [], []
            d1 = delta1(row, rec1, prev, pid)
            d2 = delta2(row, rec2, prev, pid)
            sum1 = sum(abs(x) for x in d1)
            sum2 = sum(abs(x) for x in d2)

            if sum1 <= sum2:
                deltas = d1
                rec = rec1
                modes.append(0)
                delta_mode_counts[0] += 1
            else:
                deltas = d2
                rec = rec2
                modes.append(1)
                delta_mode_counts[1] += 1

            for d in deltas:
                encoded.extend(write_varint(zigzag_encode(d)))
            prev = rec

        preds_all.extend(preds)
        modes_all.extend(modes)
        compressed = lzma.compress(bytes(encoded), preset=(9 | lzma.PRESET_EXTREME))
        blocks.append(compressed)

    for pid in preds_all:
        hdr.append(pid)
    hdr += bytes(modes_all)  # modo por fila

    with open(outfile, 'wb') as f:
        f.write(hdr)
        for comp in blocks:
            f.write(write_varint(len(comp)))
            f.write(comp)

    print("Uso de predictores:", predictor_counts)
    print("Uso de modos de delta:", delta_mode_counts)

def decompress_file(infile, outfile):
    f = open(infile, 'rb')
    if f.read(4) != MAGIC:
        raise ValueError("Formato inválido")
    num_rows = read_varint(f)
    lengths = [read_varint(f) for _ in range(num_rows)]
    if sum(lengths) == 0:
        open(outfile, 'w').close()
        return
    h0 = zigzag_decode(read_varint(f))
    preds = [ord(f.read(1)) for _ in range(num_rows)]
    modes = list(f.read(num_rows))
    blocks = []
    while True:
        try:
            bl = read_varint(f)
            blocks.append(f.read(bl))
        except EOFError:
            break

    rows = []
    prev = None
    pid_index = 0
    row_index = 0
    for block in blocks:
        decompressed = lzma.decompress(block)
        stream = BytesIO(decompressed)
        for _ in range(min(BLOCK_SIZE, num_rows - row_index)):
            L = lengths[row_index]
            pid = preds[pid_index]
            mode = modes[pid_index]
            pid_index += 1
            if L == 0:
                rows.append([]); prev = []
                row_index += 1
                continue
            rec = []
            if row_index == 0:
                rec.append(h0)
                d1 = zigzag_decode(read_varint(stream))
                rec.append(rec[0] + d1)
                for _ in range(2, L):
                    d = zigzag_decode(read_varint(stream))
                    rec.append(2 * rec[-1] - rec[-2] + d)
            else:
                for j in range(L):
                    d = zigzag_decode(read_varint(stream))
                    if mode == 0:
                        if j == 0:
                            pred = prev[0]
                        else:
                            if pid == P_LEFT:
                                pred = rec[j - 1]
                            elif pid == P_UP:
                                pred = prev[j]
                            elif pid == P_PAETH:
                                pred = paeth(rec[j - 1], prev[j], prev[j - 1])
                            elif pid == P_MED:
                                pred = med(rec[j - 1], prev[j], prev[j - 1])
                            else:
                                raise ValueError(f"Predictor desconocido: {pid}")
                        rec.append(pred + d)
                    else:
                        if j == 0:
                            if pid == P_LEFT:
                                pred = 0
                            elif pid == P_UP:
                                pred = prev[j]
                            elif pid == P_PAETH:
                                pred = paeth(0, prev[j], 0)
                            elif pid == P_MED:
                                pred = med(0, prev[j], 0)
                            else:
                                raise ValueError(f"Predictor desconocido: {pid}")
                            rec.append(pred + d)
                        elif j == 1:
                            rec.append(rec[j - 1] + d)
                        else:
                            rec.append(2 * rec[j - 1] - rec[j - 2] + d)
            rows.append(rec)
            prev = rec
            row_index += 1

    with open(outfile, 'w') as out:
        for r in rows:
            out.write(' '.join(map(str, r)) + '\n')


def main():
    args = sys.argv[1:]
    verify = '--verify' in args
    if verify: args.remove('--verify')
    if len(args) != 2:
        print("Uso: compress.py infile outfile [--verify]"); return
    inp, out = args
    t0 = time.time()
    data = open(inp, 'rb').read(4)
    if data == MAGIC:
        print("-> Descomprimiendo")
        decompress_file(inp, out)
    else:
        print("-> Comprimiendo")
        compress_file(inp, out)
        if verify:
            tmp = tempfile.mktemp()
            decompress_file(out, tmp)
            ok = open(inp).read() == open(tmp).read()
            print("✔️ Verificado" if ok else "❌ Mismatch")
            os.remove(tmp)
    dt = time.time() - t0
    si = os.path.getsize(inp) / 1024
    so = os.path.getsize(out) / 1024 if os.path.exists(out) else 0
    print(f"Time: {dt:.2f}s In:{si:.2f}kB Out:{so:.2f}kB Ratio:{si/so:.2f}x")

if __name__ == '__main__':
    main()