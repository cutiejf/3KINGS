import runpy, json, random

base_ctx = runpy.run_path('mth/razzledazzle_math.py')
simulate = base_ctx['simulate']

candidates = {
    'cherry_focus': [
        { 's': '🍒', 'm':1, 'w':120 },
        { 's': '🍋', 'm':2, 'w':10 },
        { 's': '🔔', 'm':4, 'w':10 },
        { 's': '🍊', 'm':6, 'w':10 },
        { 's': '🍉', 'm':10, 'w':10 },
        { 's': '⭐', 'm':20, 'w':5 },
        { 's': '💵', 'm':50, 'w':1.0 },
        { 's': '💎', 'm':100, 'w':0.5 },
        { 's': '7️⃣', 'm':200, 'w':0.2 },
        { 's': '👑', 'm':500, 'w':0.1 },
    ],
    'balanced_highs': [
        { 's': '🍒', 'm':1, 'w':40 },
        { 's': '🍋', 'm':2, 'w':30 },
        { 's': '🔔', 'm':4, 'w':40 },
        { 's': '🍊', 'm':6, 'w':30 },
        { 's': '🍉', 'm':10, 'w':30 },
        { 's': '⭐', 'm':20, 'w':18 },
        { 's': '💵', 'm':50, 'w':6.0 },
        { 's': '💎', 'm':100, 'w':2.0 },
        { 's': '7️⃣', 'm':200, 'w':1.0 },
        { 's': '👑', 'm':500, 'w':0.5 },
    ]
}

TRIALS = 200000
random_seed = 12345

for name, symbols in candidates.items():
    ctx = runpy.run_path('mth/razzledazzle_math.py')
    ctx['SYMBOLS'] = symbols
    random.seed(random_seed)
    print('\n=== Candidate:', name, '===')
    res = ctx['simulate'](trials=TRIALS, corr_prob=ctx['ROW_CORRELATION_PROB'], offset_pct=ctx['OFFSET_PCT'], cluster_prob=0.0)
    print(f"Hit rate: {res['hit_rate']*100:.3f}% | RTP: {res['rtp']:.6f} | multi_frac: {res['multi_frac']*100:.3f}%")
    total_symbols = sum(res['symbol_occurrences'].values())
    print('Literal occurrences:')
    for s, cnt in res['symbol_occurrences'].items():
        print(f"  {s}: {cnt} ({(cnt/total_symbols)*100:.2f}%)")

# Save candidates to file
with open('mth/experiments_candidates.json', 'w', encoding='utf-8') as f:
    json.dump(candidates, f, ensure_ascii=False, indent=2)
print('\nCandidates written to mth/experiments_candidates.json')
