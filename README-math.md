Three Kings Math Engine

This small Python script generates the exact distribution of ticket outcomes for the Three Kings pull-tab game.

Files
- math_engine.py — enumerates outcomes for 3 rows; outputs CSV with sim_id, probability, payout_multiplier.

Requirements
- Python 3.8+

Run (PowerShell)
```powershell
python .\math_engine.py --out outcomes.csv
```

Optional gzip output
```powershell
python .\math_engine.py --out outcomes.csv.gz
```

Notes
- The engine currently assumes the same symbol weights and payouts as the frontend `game.js` file. Update `SYMBOLS` in `math_engine.py` if you modify the frontend.
- The output `outcomes.csv` contains every possible combination of row outcomes (no-win or full-row symbol match). The expected RTP (payout multiplier) is printed to the console.
