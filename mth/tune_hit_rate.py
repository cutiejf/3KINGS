import runpy, copy, time

BASE_PATH = 'mth/razzledazzle_math.py'
ctx0 = runpy.run_path(BASE_PATH)
BASE_SYMBOLS = copy.deepcopy(ctx0['SYMBOLS'])
simulate_fn = ctx0['simulate']

TRIALS_QUICK = 100_000
TRIALS_FINAL = 1_000_000
TARGET = 0.22

# We'll scale indices 0..5 (common symbols)
def make_symbols(scale_factor):
    s = copy.deepcopy(BASE_SYMBOLS)
    for i in range(6):
        s[i]['w'] = max(0.0001, BASE_SYMBOLS[i]['w'] * scale_factor)
    # keep rare symbols as is
    for i in range(6, len(s)):
        s[i]['w'] = max(0.0001, BASE_SYMBOLS[i]['w'])
    return s

# Binary search over multiplier between 1 and 500
lo, hi = 1.0, 500.0
best = None
start = time.time()
for _ in range(20):
    mid = (lo + hi) / 2.0
    ctx = runpy.run_path(BASE_PATH)
    ctx['SYMBOLS'] = make_symbols(mid)
    res = ctx['simulate'](trials=TRIALS_QUICK, corr_prob=ctx['ROW_CORRELATION_PROB'], offset_pct=ctx['OFFSET_PCT'], cluster_prob=0.0)
    hit = res['hit_rate']
    print(f"scale={mid:.4f} -> hit={hit:.6f}, rtp={res['rtp']:.6f}")
    best = (mid, hit, res['rtp'], ctx['SYMBOLS'])
    if hit < TARGET:
        lo = mid
    else:
        hi = mid
    # small early exit if close enough
    if abs(hit - TARGET) < 0.002:
        break

print('\nBest quick candidate:')
print(f"  scale={best[0]:.4f}, hit={best[1]:.6f}, rtp={best[2]:.6f}")

# Validate best with final trials
print('\nValidating best candidate with 1,000,000 trials (this will take a minute)...')
ctx_final = runpy.run_path(BASE_PATH)
ctx_final['SYMBOLS'] = best[3]
res_final = ctx_final['simulate'](trials=TRIALS_FINAL, corr_prob=ctx_final['ROW_CORRELATION_PROB'], offset_pct=ctx_final['OFFSET_PCT'], cluster_prob=0.0)
print(f"Final hit: {res_final['hit_rate']*100:.3f}% | RTP: {res_final['avg_payout']:.6f}")

# Write final symbols
import json
with open('mth/tuned_symbols_hit.json', 'w', encoding='utf-8') as f:
    json.dump(best[3], f, ensure_ascii=False, indent=2)
print('Wrote mth/tuned_symbols_hit.json')
