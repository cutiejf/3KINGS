import runpy, random, copy, math, time

# Load simulator functions and SYMBOLS from your math script
ctx = runpy.run_path('mth/razzledazzle_math.py')
simulate = ctx['simulate']
BASE_SYMBOLS = copy.deepcopy(ctx['SYMBOLS'])

random.seed(12345)

TRIALS_QUICK = 100_000
TRIALS_FINAL = 1_000_000
MAX_CANDIDATES = 120

best = None
start = time.time()

# We'll vary multipliers for the low/mid tier symbols (indices 0..5)
for cand in range(MAX_CANDIDATES):
    # Create candidate by scaling base weights
    symbols = copy.deepcopy(BASE_SYMBOLS)
    # multipliers: small ones for common symbols between 1.0 and 6.0
    muls = [random.uniform(1.0, 6.0) for _ in range(6)]
    for i in range(6):
        symbols[i]['w'] = max(0.0001, BASE_SYMBOLS[i]['w'] * muls[i])
    # keep rare symbols similar but allow tiny jitter
    for i in range(6, len(symbols)):
        symbols[i]['w'] = max(0.0001, BASE_SYMBOLS[i]['w'] * random.uniform(0.5, 1.5))

    # patch symbols into simulate context by monkeypatching the module's SYMBOLS
    ctx_local = runpy.run_path('mth/razzledazzle_math.py')
    ctx_local['SYMBOLS'] = symbols
    simulate_local = ctx_local['simulate']

    res = simulate_local(trials=TRIALS_QUICK, corr_prob=ctx_local['ROW_CORRELATION_PROB'], offset_pct=ctx_local['OFFSET_PCT'], cluster_prob=0.0)
    hit = res['hit_rate']
    rtp = res['rtp']

    if best is None or abs(hit - 0.22) < abs(best['hit'] - 0.22):
        best = {'hit': hit, 'rtp': rtp, 'symbols': symbols, 'candidate': cand}
    # Stop early if we reached or exceeded 22% hit
    if hit >= 0.22:
        best = {'hit': hit, 'rtp': rtp, 'symbols': symbols, 'candidate': cand}
        print(f"Found candidate {cand} with hit {hit:.4f}, rtp {rtp:.6f}")
        break
    if cand % 10 == 0:
        elapsed = time.time() - start
        print(f"Tried {cand} candidates, best hit so far {best['hit']:.4f}, elapsed {elapsed:.1f}s")

# Final validation with 1M trials
print('\nBest candidate summary:')
print(f"  candidate: {best['candidate']}")
print(f"  quick-hit: {best['hit']:.6f}, quick-rtp: {best['rtp']:.6f}")

print('Running final validation with 1,000,000 trials (this may take a minute)...')
ctx_final = runpy.run_path('mth/razzledazzle_math.py')
ctx_final['SYMBOLS'] = best['symbols']
res_final = ctx_final['simulate'](trials=TRIALS_FINAL, corr_prob=ctx_final['ROW_CORRELATION_PROB'], offset_pct=ctx_final['OFFSET_PCT'], cluster_prob=0.0)
print('\nFinal results:')
print(f"  hit rate: {res_final['hit_rate']*100:.3f}%")
print(f"  avg payout per ticket (RTP): {res_final['avg_payout']:.6f}")
print('\nLiteral occurrences:')
for s, cnt in res_final['symbol_occurrences'].items():
    print(f"  {s}: {cnt}")

# Save the best symbols to a JSON for review
import json
with open('mth/best_symbols.json', 'w', encoding='utf-8') as f:
    json.dump(best['symbols'], f, ensure_ascii=False, indent=2)
print('\nBest symbol weights written to mth/best_symbols.json')
