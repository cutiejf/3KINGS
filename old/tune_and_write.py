from math_engine import tune_low_tier_weights, Decimal, build_reels, REEL_SCALE, REELS, REEL_LEN, per_row_win_probabilities, generate_outcomes, scale_payouts_to_target, write_csv
import json

# Tune
target_hit = Decimal('0.206')
print('Starting tuning to hit rate', target_hit)
mul = tune_low_tier_weights(target_hit)
print('Applied multiplier to cheap symbols:', mul)
# regenerate outcomes
REELS = build_reels()
REEL_LEN = len(REELS[0])
PER_ROW = per_row_win_probabilities()
outcomes = generate_outcomes()
hit = sum(1 for o in outcomes if o['payout_multiplier']>0) / Decimal(len(outcomes))
print('Achieved hit rate:', hit)
# scale to RTP 0.95
out_scaled, achieved, paytable = scale_payouts_to_target(outcomes, Decimal('0.95'))
print('Achieved RTP after scaling:', achieved)
write_csv(out_scaled, 'outcomes_tuned.csv')
with open('paytable.json','w',encoding='utf-8') as f:
    json.dump({k: format(v,'f') for k,v in paytable.items()}, f, ensure_ascii=False, indent=2)
print('Wrote outcomes_tuned.csv and paytable.json')
