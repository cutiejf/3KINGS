#!/usr/bin/env python3
"""
three_kings_math.py — Three Kings pull tab simulator (HIGH HIT RATE version)

Modified for ~22% hit rate and 97-99% RTP using MULTI-ROW wins strategy
KEEPS original multipliers, uses correlation + weighting for more wins
"""

import argparse
import json
import os
import random
from collections import defaultdict

# ---------------- Config ----------------
BET = 1.0

# ---------------- Config knobs ----------------
ROW_CORRELATION_PROB = 0.76
OFFSET_PCT = 0.045
CLUSTER_PROB = 0.06
REEL_SCALE = 6            # slightly longer strips for smoother distribution

# ---------------- Paytable shape (before auto-calibration) ----------------
SYMBOLS = [
    {"s": "🍒", "m": 2.41,  "w": 320},
    {"s": "🍋", "m": 5.30,  "w": 260},
    {"s": "🔔", "m": 12.53, "w": 180},
    {"s": "🍊", "m": 26.96, "w": 110},
    {"s": "🍉", "m": 57.81, "w": 70},
    {"s": "⭐", "m": 125.29,"w": 35},
    {"s": "💵", "m": 211.97,"w": 18},
    {"s": "💎", "m": 404.67,"w": 9},
    {"s": "7️⃣", "m": 818.98,"w": 4},
    {"s": "👑", "m": 1735.00,"w": 2},
]




PROB_SCALE = 1_000_000_000
PAYOUT_SCALE = 100

# ---------------- Helpers ----------------
def build_reels(scale=REEL_SCALE):
    """Build three reel strips with weighted run-length clustering.
    
    Creates longer runs to increase multi-row match probability.
    """
    total_w = sum(float(x["w"]) for x in SYMBOLS)
    desired_total = max(50, int(total_w * scale))

    syms = [sym["s"] for sym in SYMBOLS]
    weights = [float(sym["w"]) for sym in SYMBOLS]
    weight_sum = sum(weights)
    probs = [w / weight_sum for w in weights]

    def build_strip():
        strip = []
        # Long runs for clustering
        max_run = max(4, int(scale * 3))
        while len(strip) < desired_total:
            s = random.choices(syms, probs, k=1)[0]
            # Common symbols get longer runs
            sym_weight = next(sym["w"] for sym in SYMBOLS if sym["s"] == s)
            run_factor = sym_weight / 400
            run_length = int(random.randint(2, max_run) * (0.5 + run_factor * 0.8))
            run_length = max(3, min(run_length, 18))
            take = min(run_length, desired_total - len(strip))
            strip.extend([s] * take)
        # Light shuffle
        for _ in range(len(strip) // 25):
            i, j = random.randrange(len(strip)), random.randrange(len(strip))
            strip[i], strip[j] = strip[j], strip[i]
        return strip

    r1 = build_strip()
    r2 = build_strip()
    r3 = build_strip()
    return [r1, r2, r3]

def m_for(symbol: str) -> float:
    for sym in SYMBOLS:
        if sym["s"] == symbol:
            return float(sym["m"])
    return 0.0

# ---------------- Simulation ----------------
def simulate(trials=200_000, corr_prob=ROW_CORRELATION_PROB, offset_pct=OFFSET_PCT, cluster_prob=CLUSTER_PROB):
    reels = build_reels()
    L = len(reels[0])
    max_off = max(1, int(L * offset_pct))

    total_win = 0.0
    wins = 0
    multi = 0
    single_line_tickets = 0
    double_line_tickets = 0
    triple_line_tickets = 0

    symbol_wins = {sym["s"]: 0 for sym in SYMBOLS}
    symbol_occurrences = {sym["s"]: 0 for sym in SYMBOLS}

    buckets = defaultdict(int)
    ticket_payout_counts = defaultdict(int)

    for _ in range(trials):
        if cluster_prob and random.random() < cluster_prob:
            base = random.randrange(L)
            i = j = k = base
        elif random.random() < corr_prob:
            base = random.randrange(L)
            off1 = random.randint(-max_off, max_off)
            off2 = random.randint(-max_off, max_off)
            i, j, k = base, (base + off1) % L, (base + off2) % L
        else:
            i, j, k = random.randrange(L), random.randrange(L), random.randrange(L)

        ticket_win = 0.0
        hit_rows = 0

        for r in range(3):
            a = reels[0][(i + r) % L]
            b = reels[1][(j + r) % L]
            c = reels[2][(k + r) % L]

            symbol_occurrences[a] += 1
            symbol_occurrences[b] += 1
            symbol_occurrences[c] += 1

            if a == b == c:
                pay = m_for(a)
                ticket_win += pay
                hit_rows += 1
                symbol_wins[a] += 1
                buckets[float(pay)] += 0

        if hit_rows > 0:
            wins += 1
            if hit_rows > 1:
                multi += 1
            if hit_rows == 1:
                single_line_tickets += 1
            elif hit_rows == 2:
                double_line_tickets += 1
            elif hit_rows == 3:
                triple_line_tickets += 1

        total_win += ticket_win
        buckets[float(round(ticket_win, 4))] += 1
        ticket_payout_counts[float(round(ticket_win, 4))] += 1

    avg_payout = total_win / trials
    rtp = avg_payout / BET
    hit_rate = wins / trials
    multi_frac = (multi / wins) if wins else 0.0

    return {
        "trials": trials,
        "rtp": rtp,
        "avg_payout": avg_payout,
        "hit_rate": hit_rate,
        "multi_frac": multi_frac,
        "buckets": dict(sorted(buckets.items())),
        "ticket_payout_counts": dict(sorted(ticket_payout_counts.items())),
        "single_line_tickets": single_line_tickets,
        "double_line_tickets": double_line_tickets,
        "triple_line_tickets": triple_line_tickets,
        "symbol_wins": dict(symbol_wins),
        "symbol_occurrences": dict(symbol_occurrences),
    }

# ---------------- Stake artifacts ----------------
def write_stake_artifacts(results, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    payout_counts = results["ticket_payout_counts"]
    total = results["trials"]
    unique_payouts = sorted(payout_counts.keys())
    payout_to_id = {p: idx + 1 for idx, p in enumerate(unique_payouts)}

    csv_path = os.path.join(out_dir, "lookUpTable_base.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("simulation number,round probability,payout multiplier\n")
        for p in unique_payouts:
            prob = payout_counts[p] / total
            scaled_prob = int(round(prob * PROB_SCALE))
            scaled_pay = int(round(p * PAYOUT_SCALE))
            sim_id = payout_to_id[p]
            f.write(f"{sim_id},{scaled_prob},{scaled_pay}\n")

    jsonl_name = "books_base.jsonl"
    jsonl_path = os.path.join(out_dir, jsonl_name)
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for p in unique_payouts:
            book_id = payout_to_id[p]
            scaled_pay = int(round(p * PAYOUT_SCALE))
            book = {
                "id": book_id,
                "payoutMultiplier": scaled_pay,
                "events": [{"index": 0, "type": "reveal", "ticket_total": float(p)}],
                "criteria": "base",
                "baseGameWins": float(p),
                "freeGameWins": 0.0
            }
            f.write(json.dumps(book) + "\n")

    index = {"modes": [{"name": "base", "cost": 1.0,
                        "events": jsonl_name, "weights": "lookUpTable_base.csv"}]}
    index_path = os.path.join(out_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    return {"csv": csv_path, "jsonl": jsonl_path, "index": index_path}

# ---------------- Main ----------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=200_000)
    parser.add_argument("--corr", type=float, default=ROW_CORRELATION_PROB)
    parser.add_argument("--offset", type=float, default=OFFSET_PCT)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--out", type=str, default=os.path.join(os.path.dirname(__file__), "stake_outcomes"))
    parser.add_argument("--cluster", type=float, default=CLUSTER_PROB, help="fraction of tickets forced to identical starts (i==j==k)")
    args = parser.parse_args()

    random.seed(args.seed)
    res = simulate(trials=args.trials, corr_prob=args.corr, offset_pct=args.offset, cluster_prob=args.cluster)

    print(f"Simulated {res['trials']} tickets")
    print(f"Hit rate: {res['hit_rate']*100:.3f}%")
    print(f"Avg payout per ticket: {res['avg_payout']:.6f}  RTP: {res['rtp']:.6f}")
    print(f"Multi-row fraction of wins: {res['multi_frac']*100:.3f}%\n")

    print("Ticket line win breakdown:")
    print(f"  Single-line tickets: {res['single_line_tickets']}")
    print(f"  Double-line tickets: {res['double_line_tickets']}")
    print(f"  Triple-line tickets: {res['triple_line_tickets']}\n")

    print("Winning symbol totals:")
    for sym, cnt in res["symbol_wins"].items():
        if cnt > 0:
            print(f"  {sym}: {cnt}")

    print("\nLiteral symbol occurrences (all appearances):")
    total_symbols = sum(res["symbol_occurrences"].values())
    for sym, cnt in res["symbol_occurrences"].items():
        pct = (cnt / total_symbols) * 100
        print(f"  {sym}: {cnt} ({pct:.2f}%)")

    paths = write_stake_artifacts(res, args.out)
    print("\nArtifacts written:")
    for k, v in paths.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()