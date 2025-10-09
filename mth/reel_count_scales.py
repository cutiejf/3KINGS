import runpy, random
mod = runpy.run_path('mth/razzledazzle_math.py')
build_reels = mod['build_reels']

for scale in (2, 10, 20, 50):
    random.seed(12345)
    reels = build_reels(scale=scale)
    L = len(reels[0])
    symbols = ['🍒','🍋','🔔','🍊','🍉','⭐','💵','💎','7️⃣','👑']
    counts = {s: [reel.count(s) for reel in reels] for s in symbols}
    print(f"scale={scale}, L={L}")
    for sym, c in counts.items():
        print(f"  {sym}: {c}")
    print()
