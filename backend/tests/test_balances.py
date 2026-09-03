import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.balances import equal_split_cents, compute_net_balances, simplify_debts


def test_equal_split_cent_exact_with_remainder():
    # 1000 cents / 3 people does not divide evenly.
    shares = equal_split_cents(1000, [1, 2, 3])
    assert sum(shares.values()) == 1000
    # first (remainder) people get the extra cent
    assert shares[1] == 334
    assert shares[2] == 333
    assert shares[3] == 333


def test_equal_split_exact_division():
    shares = equal_split_cents(900, [1, 2, 3])
    assert shares == {1: 300, 2: 300, 3: 300}


def test_net_balances_single_expense_two_people():
    # A pays 1000 for a dinner split equally between A and B.
    expenses = [
        {
            "paid_by": "A",
            "splits": [
                {"user": "A", "amount_cents": 500},
                {"user": "B", "amount_cents": 500},
            ],
        }
    ]
    net = compute_net_balances(expenses, [])
    assert net["A"] == 500   # A is owed 500
    assert net["B"] == -500  # B owes 500


def test_net_balances_settlement_reduces_debt():
    expenses = [
        {
            "paid_by": "A",
            "splits": [
                {"user": "A", "amount_cents": 500},
                {"user": "B", "amount_cents": 500},
            ],
        }
    ]
    settlements = [{"from_user": "B", "to_user": "A", "amount_cents": 500}]
    net = compute_net_balances(expenses, settlements)
    assert net["A"] == 0
    assert net["B"] == 0


def test_simplify_debts_three_people_reduces_transaction_count():
    # A paid for everyone, B paid for a bit, C paid nothing.
    # Classic scenario: naive pairwise view has many edges, simplified has few.
    net = {"A": 800, "B": -300, "C": -500}
    txns = simplify_debts(net)

    # Every dollar owed must be accounted for.
    assert sum(t["amount_cents"] for t in txns if t["to_user"] == "A") == 800
    # Should not produce more transactions than debtors.
    assert len(txns) <= 2
    for t in txns:
        assert t["amount_cents"] > 0
        assert t["from_user"] != t["to_user"]


def test_simplify_debts_all_settled_produces_no_transactions():
    net = {"A": 0, "B": 0, "C": 0}
    assert simplify_debts(net) == []


def test_full_flow_three_person_trip():
    """
    A pays 900 for hotel (split A/B/C), B pays 300 for gas (split A/B/C).
    Verify final simplified debts settle everyone to zero when applied back.
    """
    expenses = [
        {
            "paid_by": "A",
            "splits": [
                {"user": "A", "amount_cents": 300},
                {"user": "B", "amount_cents": 300},
                {"user": "C", "amount_cents": 300},
            ],
        },
        {
            "paid_by": "B",
            "splits": [
                {"user": "A", "amount_cents": 100},
                {"user": "B", "amount_cents": 100},
                {"user": "C", "amount_cents": 100},
            ],
        },
    ]
    net = compute_net_balances(expenses, [])
    txns = simplify_debts(net)

    # Apply the simplified transactions back and confirm everyone nets to zero.
    check = dict(net)
    for t in txns:
        check[t["from_user"]] += t["amount_cents"]
        check[t["to_user"]] -= t["amount_cents"]
    assert all(v == 0 for v in check.values())
