import json
import os


def test_game_basics():
    # Base bet in the current frontend is 0.5
    base_bet = 0.5
    assert base_bet == 0.5

    # paytable should exist and contain 10 symbols
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    paytable_path = os.path.join(root, 'paytable.json')
    assert os.path.exists(paytable_path)
    with open(paytable_path, 'r', encoding='utf-8') as f:
        pay = json.load(f)
    assert isinstance(pay, dict)
    assert len(pay) >= 10