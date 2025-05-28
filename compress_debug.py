#!/usr/bin/env python3
import sys, os, time, lzma
from io import BytesIO

MAGIC = b'BPR1'  # Block Predictor + Range (LZMA) v1
P_LEFT  = 0
P_UP    = 1
P_PAETH = 2

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

def zigzag_encode(n:int)->int:
    return (n<<1) ^ (n>>31)
def zigzag_decode(z:int)->int:
    return (z>>1) ^ -(z&1)

def select_predictor_for_row(row, prev_row):
    # Try Left, Up, Paeth, pick minimal sum(abs(delta))
    sums = [0,0,0]
    for pid in (P_LEFT,P_UP,P_PAETH):
        total = 0
        for i,v in enumerate(row):
            if prev_row is None and i==0:
                continue
            if pid==P_LEFT:
                pred = row[i-1] if i>0 else 0
            elif pid==P_UP:
                pred = prev_row[i] if prev_row and i<len(prev_row) else 0
            else:
                a = row[i-1] if i>0 else 0
                b = prev_row[i] if prev_row and i<len(prev_row) else 0
                c = prev_row[i-1] if prev_row and i>0 else 0
                pred=paeth(a,b,c)
            total += abs(v-pred)
        sums[pid]=total
    return min(( (sums[i],i) for i in (P_LEFT,P_UP,P_PAETH) ))[1]

def compress_file(infile,outfile):
    rows = [ list(map(int,line.split())) for line in open(infile) ]
    num_rows = len(rows)
    # Header
    hdr = bytearray()
    hdr += MAGIC
    hdr += write_varint(num_rows)
    # lengths varint
    for r in rows:
        hdr += write_varint(len(r))
    # Flatten for h0
    flat = [x for r in rows for x in r]
    total = len(flat)
    if total==0:
        open(outfile,'wb').write(hdr)
        return
    # h0
    h0 = flat[0]
    hdr += write_varint(zigzag_encode(h0))
    # We'll store predictor id per row
    preds = []
    prev=None
    # Prepare all compressed blocks
    blocks = []
    for row in rows:
        pid = select_predictor_for_row(row, prev)
        preds.append(pid)
        # compute residuals
        rec=[]; deltas=[]
        for i,v in enumerate(row):
            if prev is None and i==0:
                rec.append(v); continue
            if pid==P_LEFT:
                pred = rec[i-1] if i>0 else 0
            elif pid==P_UP:
                pred = prev[i] if prev and i<len(prev) else 0
            else:
                a = rec[i-1] if i>0 else 0
                b = prev[i] if prev and i<len(prev) else 0
                c = prev[i-1] if prev and i>0 else 0
                pred=paeth(a,b,c)
            deltas.append(v-pred)
            rec.append(v)
        prev=rec
        # ZigZag+varint encode
        raw=bytearray()
        for d in deltas:
            zd = zigzag_encode(d)
            raw.extend(write_varint(zd))
        # Compress this row
        comp = lzma.compress(bytes(raw), preset=(9|lzma.PRESET_EXTREME))
        blocks.append(comp)
    # Append predictor ids
    for pid in preds:
        hdr.append(pid)
    # Now write file
    with open(outfile,'wb') as f:
        f.write(hdr)
        # For each block: length + data
        for comp in blocks:
            f.write(write_varint(len(comp)))
            f.write(comp)

def decompress_file(infile,outfile):
    f=open(infile,'rb')
    if f.read(4)!=MAGIC:
        raise ValueError("Formato inválido")
    num_rows = read_varint(f)
    lengths  = [read_varint(f) for _ in range(num_rows)]
    total = sum(lengths)
    if total==0:
        open(outfile,'w').close(); return
    h0 = zigzag_decode(read_varint(f))
    # read comp for each row
    # but first we need predictor ids
    # we'll read them after reading all row-lengths?
    # Actually preds are written *after* all blocks in our scheme...
    # So we need a two-pass: read blocks first, store them, then read preds.
    blocks=[]
    for _ in range(num_rows):
        bl = read_varint(f)
        blocks.append(f.read(bl))
    preds = [ord(f.read(1)) for _ in range(num_rows)]
    # reconstruct
    rows=[]; prev=None
    for row_idx,(L,comp,pid) in enumerate(zip(lengths,blocks,preds)):
        if L==0:
            rows.append([]); prev=[]
            continue
        if row_idx==0: 
            # first row: h0 + rest deltas
            rem = lzma.decompress(comp)
            stream = BytesIO(rem)
            deltas=[ zigzag_decode(read_varint(stream)) for _ in range(L-1) ]
            rec=[h0]
            for d in deltas:
                rec.append(rec[-1]+d)  # for row0, pred left of rec[-1]
            rows.append(rec); prev=rec; continue
        # other rows
        rem = lzma.decompress(comp)
        stream = BytesIO(rem)
        deltas=[ zigzag_decode(read_varint(stream)) for _ in range(L) ]
        rec=[]; di=0
        for i in range(L):
            if i==0:
                # first element: pred? rec empty => pred= prev[0] for UP? left? you choose
                # original code wrote no delta for first element; here we do row-based
                # Simpler: assume d0 is pred=prev[0]
                pred = prev[0]
                val = pred + deltas[di]; di+=1
                rec.append(val)
            else:
                if pid==P_LEFT:
                    pred=rec[i-1]
                elif pid==P_UP:
                    pred=prev[i]
                else:
                    a=rec[i-1]; b=prev[i]; c=prev[i-1]
                    pred=paeth(a,b,c)
                val=pred + deltas[di]; di+=1
                rec.append(val)
        rows.append(rec); prev=rec
    # write text
    with open(outfile,'w') as out:
        for r in rows:
            out.write(' '.join(map(str,r))+'\n')

def main():
    args=sys.argv[1:]
    verify='--verify' in args
    if verify: args.remove('--verify')
    if len(args)!=2:
        print("Uso: compress.py infile outfile [--verify]"); return
    inp,out = args
    t0=time.time()
    data=open(inp,'rb').read(4)
    if data==MAGIC:
        print("-> Descomprimiendo")
        decompress_file(inp,out)
    else:
        print("-> Comprimiendo")
        compress_file(inp,out)
        if verify:
            tmp=tempfile.mktemp()
            decompress_file(out,tmp)
            ok = open(inp).read()==open(tmp).read()
            print("✔️ Verificado" if ok else "❌ Mismatch")
            os.remove(tmp)
    dt=time.time()-t0
    si=os.path.getsize(inp)/1024
    so=os.path.getsize(out)/1024 if os.path.exists(out) else 0
    print(f"Time: {dt:.2f}s In:{si:.2f}kB Out:{so:.2f}kB Ratio:{si/so:.2f}x")

if __name__=='__main__':
    main()
