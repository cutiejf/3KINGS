"""Three Kings Math Engine (refactored)

This module provides:
- precise probability computation using Decimal
- full enumeration of ticket outcomes (per-row wins and no-win cases)
- a deterministic ticket generator for a given outcome id
- RTP and probability-sum tests

Usage examples (PowerShell):
  python .\math_engine.py --out outcomes.csv          # write CSV and print RTP
  python .\math_engine.py --test                    # run probability & RTP tests
  python .\math_engine.py --sample 10               # print first 10 outcomes

The CSV format: sim_id, probability, payout_multiplier
Probability is relative to a single ticket; payout_multiplier is in "base-bet units"
To get a currency amount for a bet: payout = payout_multiplier * (bet / BET_base)
"""

from decimal import Decimal, getcontext
import csv
import gzip
import argparse
from itertools import product
import random
from typing import List, Tuple, Dict

# increase precision for probability math
getcontext().prec = 28

# === CONFIG / SYMBOL DEFINITIONS ===
# Use Decimal for weights and payouts to avoid fp drift in accumulations
SYMBOLS = [
    { 's': '🍒', 'p': Decimal('0.5'),  'm': Decimal('1'),    'w': Decimal('35') },
    { 's': '🍋', 'p': Decimal('1'),    'm': Decimal('2'),    'w': Decimal('28') },
    { 's': '🔔', 'p': Decimal('2'),    'm': Decimal('4'),    'w': Decimal('14') },
    { 's': '🍊', 'p': Decimal('3'),    'm': Decimal('6'),    'w': Decimal('9')  },
    { 's': '🍉', 'p': Decimal('5'),    'm': Decimal('10'),   'w': Decimal('8')  },
    { 's': '⭐', 'p': Decimal('10'),   'm': Decimal('20'),   'w': Decimal('5')  },
    { 's': '💵', 'p': Decimal('25'),   'm': Decimal('50'),   'w': Decimal('0.6') },
    { 's': '💎', 'p': Decimal('50'),   'm': Decimal('100'),  'w': Decimal('0.25')},
    { 's': '7️⃣', 'p': Decimal('100'), 'm': Decimal('200'),  'w': Decimal('0.1') },
    { 's': '👑', 'p': Decimal('250'),  'm': Decimal('500'),  'w': Decimal('0.05')},
]

# base bet used in frontend to scale payouts (BET.base)
BET_BASE = Decimal('0.5')
BET_BASE = Decimal('0.5')

# Build a reel-strip model from symbol weights so probabilities are grounded in an explicit
# sample space. We convert weights to integer counts using REEL_SCALE so fractional weights
# (like 0.5, 1.5) map to whole counts on the reel.
REEL_SCALE = 2

def build_reels(scale: int = REEL_SCALE, reels: int = 3) -> List[List[str]]:
    """Construct `reels` identical reels where each symbol appears int(w * scale) times.

    Returns a list of reels (each a list of symbol strings).
    """
    base_reel: List[str] = []
    for sym in SYMBOLS:
        # sym['w'] may be Decimal or float-like; ensure Decimal multiplication
        count = int((Decimal(sym['w']) * Decimal(scale)).to_integral_value(rounding='ROUND_DOWN'))
        if count <= 0:
            continue
        base_reel.extend([sym['s']] * count)
    return [list(base_reel) for _ in range(reels)]


REELS = build_reels()
REEL_LEN = len(REELS[0])


def build_reels_with_multiplier(mult: Decimal, reels: int = 3, scale: int = REEL_SCALE) -> List[List[str]]:
    """Build reels where low-tier symbols are multiplied by `mult` before scaling to integers."""
    low_symbols = { '🍒', '🍋', '🔔', '🍊', '🍉' }  # low-tier set
    base_reel: List[str] = []
    for sym in SYMBOLS:
        w = Decimal(sym['w'])
        if sym['s'] in low_symbols:
            w = w * Decimal(mult)
        count = int((w * Decimal(scale)).to_integral_value(rounding='ROUND_DOWN'))
        if count <= 0:
            continue
        base_reel.extend([sym['s']] * count)
    if not base_reel:
        return [list(base_reel) for _ in range(reels)]
    return [list(base_reel) for _ in range(reels)]


def per_row_prob_from_reel(reels: List[List[str]]) -> Decimal:
    """Compute the per-row three-of-a-kind probability for identical reels (sum over symbols (cnt/len)^3)."""
    if not reels or not reels[0]:
        return Decimal('0')
    counts: Dict[str,int] = {}
    L = len(reels[0])
    for s in reels[0]:
        counts[s] = counts.get(s, 0) + 1
    prob = Decimal('0')
    for sym in SYMBOLS:
        cnt = counts.get(sym['s'], 0)
        col_prob = Decimal(cnt) / Decimal(L)
        prob += col_prob ** 3
    return prob


def tune_multiplier_for_hit_rate(target_hit: Decimal, tol: Decimal = Decimal('1e-4'), max_iter: int = 30) -> Decimal:
    """Binary search multiplier for low-tier weights to achieve approx target per-ticket hit rate.

    Uses approximation that rows are independent: hit_rate ~= 1 - (1 - p_row)^3.
    Returns the multiplier (Decimal).
    """
    # target per-row probability required under independence approximation
    target_row = Decimal('1') - (Decimal('1') - target_hit) ** (Decimal('1')/Decimal(3))
    lo = Decimal('1')
    hi = Decimal('10')
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        reels = build_reels_with_multiplier(mid)
        p_row = per_row_prob_from_reel(reels)
        approx_hit = Decimal('1') - (Decimal('1') - p_row) ** 3
        if abs(approx_hit - target_hit) <= tol:
            return mid
        if approx_hit < target_hit:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


# === PER-ROW PROBABILITIES (reel-based) ===
def per_row_win_probabilities() -> Dict[str, Dict[str, Decimal]]:
    """Return mapping symbol -> {'prob': Decimal, 'payout': Decimal} where prob is prob that a row is SSS
    when each column is sampled from its reel (reels assumed independent).
    """
    d: Dict[str, Dict[str, Decimal]] = {}
    # compute counts on a single reel
    counts: Dict[str, int] = {}
    for s in REELS[0]:
        counts[s] = counts.get(s, 0) + 1
    for sym in SYMBOLS:
        cnt = counts.get(sym['s'], 0)
        col_prob = Decimal(cnt) / Decimal(REEL_LEN) if REEL_LEN > 0 else Decimal('0')
        prob = col_prob ** 3
        d[sym['s']] = { 'prob': prob, 'payout': sym['p'] }
    return d


PER_ROW = per_row_win_probabilities()
P_NO_WIN = Decimal('1') - sum(v['prob'] for v in PER_ROW.values())

# row_options: tuples of (symbol_or_None, probability)
ROW_OPTIONS: List[Tuple[str, Decimal]] = [(None, P_NO_WIN)] + [(sym['s'], PER_ROW[sym['s']]['prob']) for sym in SYMBOLS]

# === OUTCOME ENUMERATION ===
def generate_outcomes() -> List[Dict]:
    """Enumerate the full ticket outcome space by iterating reel start indices.

    We model three reels (REELS[0..2]) and choose an integer start position for each reel.
    The visible 3-row window for a reel starting at index i is [reel[i], reel[i+1], reel[i+2]] (wrap-around).
    Each distinct triple of start indices (i,j,k) defines a unique ticket. The probability of each
    ticket is 1 / (REEL_LEN ** 3) assuming uniform reel stops.

    Returns list of dicts: { 'sim_id': int, 'prob': Decimal, 'payout_multiplier': Decimal, 'rows': ((r1c1,r1c2,r1c3), (r2...), (r3...)) }
    where each row is a triple of symbols (left-to-right).
    """
    outcomes: List[Dict] = []
    idx = 0
    if REEL_LEN == 0:
        return outcomes
    prob_each = Decimal(1) / (Decimal(REEL_LEN) ** 3)
    # iterate all start indices for the three reels
    for i in range(REEL_LEN):
        for j in range(REEL_LEN):
            for k in range(REEL_LEN):
                # build 3 rows; row r uses offsets (i+r, j+r, k+r)
                rows = []
                payout = Decimal('0')
                for r in range(3):
                    a = REELS[0][(i + r) % REEL_LEN]
                    b = REELS[1][(j + r) % REEL_LEN]
                    c = REELS[2][(k + r) % REEL_LEN]
                    rows.append((a, b, c))
                    if a == b == c:
                        payout += PER_ROW[a]['payout']
                outcomes.append({ 'sim_id': idx, 'prob': prob_each, 'payout_multiplier': payout, 'rows': tuple(rows) })
                idx += 1
    return outcomes


def rtp_from_outcomes(outcomes: List[Dict]) -> Decimal:
    """Compute expected payout multiplier (in base-bet units)."""
    expected = sum(o['prob'] * o['payout_multiplier'] for o in outcomes)
    return expected


def scale_payouts_to_target(outcomes: List[Dict], target_rtp: Decimal) -> Tuple[List[Dict], Decimal, Dict[str, Decimal]]:
    """Scale per-symbol payouts uniformly to reach target RTP.

    Returns (new_outcomes, achieved_rtp, paytable) where paytable maps symbol->scaled_payout.
    Scaling is linear on the per-symbol `p` values.
    """
    if target_rtp <= 0:
        return outcomes, rtp_from_outcomes(outcomes), {s['s']: s['p'] for s in SYMBOLS}

    # current RTP
    current = rtp_from_outcomes(outcomes)
    if current == 0:
        return outcomes, current, {s['s']: s['p'] for s in SYMBOLS}

    scale = target_rtp / current
    # create paytable of scaled payouts
    paytable: Dict[str, Decimal] = { s['s']: (s['p'] * scale).quantize(Decimal('0.0000000001')) for s in SYMBOLS }

    # apply paytable to outcomes
    new_outcomes: List[Dict] = []
    for o in outcomes:
        new_payout = Decimal('0')
        # rows in outcome are tuples like ( (a,b,c), (a,b,c), (a,b,c) )
        for row in o['rows']:
            a,b,c = row
            if a == b and b == c:
                new_payout += paytable[a]
        new_outcomes.append({ **o, 'payout_multiplier': new_payout })

    achieved = rtp_from_outcomes(new_outcomes)
    return new_outcomes, achieved, paytable


def compute_hit_rate(outcomes: List[Dict]) -> Decimal:
    """Compute fraction of tickets that have at least one winning row."""
    total = Decimal(len(outcomes))
    winners = sum(1 for o in outcomes if o['payout_multiplier'] > 0)
    return Decimal(winners) / total if total > 0 else Decimal('0')


def tune_low_tier_weights(target_hit: Decimal, cheap_threshold: Decimal = Decimal('5')) -> Decimal:
    """Tune low-tier symbol weights by scaling weights for symbols with payout <= cheap_threshold.

    Returns the final multiplier applied to those weights.
    This is a simple binary-search style search over a multiplier factor.
    """
    # We'll search multiplier in [1, 20]
    lo = Decimal('1')
    hi = Decimal('20')
    best_mul = lo
    for _ in range(20):
        mid = (lo + hi) / 2
        # apply mid multiplier to cheap symbols and rebuild reels
        for s in SYMBOLS:
            # store original weight in a temp key if not present
            if 'orig_w' not in s:
                s['orig_w'] = s['w']
            if s['p'] <= cheap_threshold:
                s['w'] = (s['orig_w'] * mid)
            else:
                s['w'] = s['orig_w']
        # rebuild reels and outcomes
        global REELS, REEL_LEN, PER_ROW
        REELS = build_reels()
        REEL_LEN = len(REELS[0])
        PER_ROW = per_row_win_probabilities()
        outcomes = generate_outcomes()
        hit = compute_hit_rate(outcomes)
        # print('test mul', mid, 'hit', hit)
        if hit < target_hit:
            lo = mid
        else:
            hi = mid
            best_mul = mid
    # keep final weights applied
    for s in SYMBOLS:
        if 'orig_w' in s and s['p'] <= cheap_threshold:
            s['w'] = (s['orig_w'] * best_mul)
    # rebuild final structures
    REELS = build_reels()
    REEL_LEN = len(REELS[0])
    PER_ROW = per_row_win_probabilities()
    return best_mul


def write_csv(outcomes: List[Dict], outpath: str, gzip_out: bool=False) -> None:
    headers = ['sim_id', 'probability', 'payout_multiplier']
    rows = [ (o['sim_id'], o['prob'], o['payout_multiplier']) for o in outcomes ]
    if gzip_out or outpath.endswith('.gz'):
        with gzip.open(outpath, 'wt', newline='') as f:
            w = csv.writer(f)
            w.writerow(headers)
            for sim_id, prob, payout in rows:
                w.writerow([sim_id, format(prob, 'f'), format(payout, 'f')])
    else:
        with open(outpath, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(headers)
            for sim_id, prob, payout in rows:
                w.writerow([sim_id, format(prob, 'f'), format(payout, 'f')])


# === TICKET GENERATION (canonical) ===
def weighted_symbol_choice() -> str:
    """Pick a symbol by sampling uniformly from a reel (returns symbol string)."""
    if REEL_LEN == 0:
        return SYMBOLS[0]['s']
    # sample from the base reel (all reels are identical)
    return random.choice(REELS[0])


def generate_ticket_for_outcome(outcome: Dict) -> List[Tuple[str,str,str]]:
    """Produce a concrete ticket (3 rows x 3 positions) for a given enumerated outcome.

    - For winning rows (symbol S), returns (S,S,S).
    - For non-winning rows (None), produces a deterministic triple that is not three-of-a-kind
      by sampling weighted choices and fixing the third if it accidentally matches the first two.

    This is a canonical representative ticket for that outcome; Stake ingestion may accept
    only the final payouts, but this allows reconstructing a plausible ticket layout.
    """
    ticket = []
    for sym in outcome['rows']:
        if sym is not None:
            ticket.append((sym, sym, sym))
        else:
            # produce a plausible non-winning triple by sampling each column from its reel
            # and ensuring the triple is not three-of-a-kind. If it is, alter the third symbol.
            a = random.choice(REELS[0])
            b = random.choice(REELS[1]) if len(REELS) > 1 else random.choice(REELS[0])
            c = random.choice(REELS[2]) if len(REELS) > 2 else random.choice(REELS[0])
            if a == b == c:
                # change c to a different symbol by choosing a different index on reel 2
                alt = next((sym['s'] for sym in SYMBOLS if sym['s'] != c), SYMBOLS[0]['s'])
                c = alt
            ticket.append((a,b,c))
    return ticket


# === TESTS / VALIDATION ===
def run_rtp_and_probability_tests(outcomes: List[Dict]) -> Dict[str, object]:
    """Run basic sanity checks: probability sums to 1 and compute RTP. Returns results dict."""
    total_prob = sum(o['prob'] for o in outcomes)
    rtp = rtp_from_outcomes(outcomes)
    results = {
        'total_prob': total_prob,
        'rtp': rtp,
        'outcome_count': len(outcomes)
    }
    # Basic assertions (raise if fails)
    # Allow tiny rounding tolerance
    tol = Decimal('1e-12')
    if abs(total_prob - Decimal('1')) > tol:
        raise AssertionError(f'Probability sum != 1 (sum={total_prob})')
    if rtp < 0 or rtp.is_nan():
        raise AssertionError(f'Invalid RTP: {rtp}')
    return results


def main():
    parser = argparse.ArgumentParser(description='Math engine for THREE KINGS')
    parser.add_argument('--out', '-o', default='outcomes.csv', help='CSV output path (use .gz to gzip)')
    parser.add_argument('--gzip', action='store_true', help='Write gzipped CSV')
    parser.add_argument('--target-rtp', type=str, default=None, help='Target RTP to scale payouts to (e.g. 0.95)')
    parser.add_argument('--hit-target', type=str, default=None, help='Target per-ticket hit rate (e.g. 0.206 for 20.6%%)')
    parser.add_argument('--test', action='store_true', help='Run probability & RTP tests and exit')
    parser.add_argument('--sample', type=int, default=0, help='Print first N outcomes and exit')
    args = parser.parse_args()

    # Optional: tune reels to reach a desired hit rate before enumerating outcomes
    paytable = None
    if args.hit_target:
        try:
            target_hit = Decimal(args.hit_target)
            mult = tune_multiplier_for_hit_rate(target_hit)
            print('Tuned low-tier multiplier to', format(mult, 'f'))
            # rebuild global REELS and REEL_LEN by monkeypatching through a rebuild
            new_reels = build_reels_with_multiplier(mult)
            # override globals used by other functions
            global REELS, REEL_LEN
            REELS = new_reels
            REEL_LEN = len(REELS[0])
        except Exception as e:
            print('Failed to tune hit target:', e)

    outcomes = generate_outcomes()

    # Optional: scale payouts to a target RTP
    if args.target_rtp:
        try:
            target = Decimal(args.target_rtp)
            outcomes, achieved, paytable = scale_payouts_to_target(outcomes, target)
            print('Scaled payouts to target:', format(target, 'f'), 'achieved:', format(achieved, 'f'))
        except Exception as e:
            print('Failed to scale payouts to target RTP:', e)

    if args.test:
        res = run_rtp_and_probability_tests(outcomes)
        print('Outcome count:', res['outcome_count'])
        print('Total probability sum:', format(res['total_prob'], 'f'))
        print('RTP (expected payout multiplier):', format(res['rtp'], 'f'))
        return

    if args.sample and args.sample > 0:
        print('First', args.sample, 'outcomes:')
        for o in outcomes[:args.sample]:
            print(o['sim_id'], format(o['prob'], 'f'), format(o['payout_multiplier'], 'f'), o['rows'])
        return

    # default: write CSV and print RTP
    write_csv(outcomes, args.out, gzip_out=args.gzip)
    rtp = rtp_from_outcomes(outcomes)
    print('Wrote outcomes to', args.out)
    print('Generated outcomes:', len(outcomes))
    print('RTP (expected payout multiplier):', format(rtp, 'f'))
    if paytable:
        import json
        with open('paytable.json','w',encoding='utf-8') as f:
            json.dump({k: format(v,'f') for k,v in paytable.items()}, f, ensure_ascii=False, indent=2)
        print('Wrote paytable.json')


if __name__ == '__main__':
    main()
