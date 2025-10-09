import runpy, random, math

# Load functions from your math file
mod = runpy.run_path('mth/razzledazzle_math.py')
build_reels = mod['build_reels']

# Use the same seed as the sim run
random.seed(12345)
reels = build_reels()
L = len(reels[0])

symbol = '💵'
counts = [reel.count(symbol) for reel in reels]

# Approximate probability per row under independent random starts: (count/L)^3
prob_per_row = (counts[0]/L) * (counts[1]/L) * (counts[2]/L)
# Three rows per ticket (approx, rows are distinct offsets)
prob_per_ticket = 3 * prob_per_row

trials = 200000
expected = prob_per_ticket * trials
p_zero = math.exp(-expected) if expected < 50 else (1 - prob_per_ticket) ** trials

print(f"Reel length L = {L}")
print(f"Counts of '{symbol}' per reel: {counts}")
print(f"Prob (single row triple) ≈ {prob_per_row:.12e}")
print(f"Prob (any of 3 rows) per ticket ≈ {prob_per_ticket:.12e}")
print(f"Expected occurrences in {trials} tickets ≈ {expected:.6f}")
print(f"Approx. probability of seeing ZERO occurrences in {trials} tickets ≈ {p_zero:.6f}")

# Also print counts for other rare symbols for context
rare_syms = ['💎','7️⃣','👑']
for s in rare_syms:
    c = [reel.count(s) for reel in reels]
    prob_row = (c[0]/L)*(c[1]/L)*(c[2]/L)
    prob_ticket = 3*prob_row
    exp = prob_ticket * trials
    print(f"\nSymbol {s}: counts {c}, expected in {trials}: {exp:.6f}")
