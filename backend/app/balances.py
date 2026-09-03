"""
Balance math, kept free of any Flask/SQLAlchemy imports on purpose.

Everything here works in integer cents and plain dicts/tuples so it can be
unit-tested without spinning up an app or a database.
"""
from collections import defaultdict


def equal_split_cents(amount_cents, user_ids):
    """
    Split amount_cents equally among user_ids, cent-exact.

    Naive `amount / n` for an amount like 1000 cents over 3 people loses or
    gains a cent depending on rounding, and repeated over many expenses that
    drift adds up to real money. Instead: everyone gets amount // n, and the
    leftover cents (amount % n) go one-each to the first `remainder` people.
    Sum of the returned shares always equals amount_cents exactly.
    """
    n = len(user_ids)
    if n == 0:
        raise ValueError("Cannot split among zero users")

    base, remainder = divmod(amount_cents, n)
    shares = {}
    for i, uid in enumerate(user_ids):
        shares[uid] = base + (1 if i < remainder else 0)
    return shares


def compute_net_balances(expenses, settlements):
    """
    expenses: iterable of {"paid_by": user_id, "splits": [{"user": user_id, "amount_cents": int}, ...]}
    settlements: iterable of {"from_user": user_id, "to_user": user_id, "amount_cents": int}

    Returns {user_id: net_cents} where positive = this user is owed money
    (a creditor), negative = this user owes money (a debtor), 0 = settled up.
    """
    net = defaultdict(int)

    for expense in expenses:
        payer = expense["paid_by"]
        total = sum(s["amount_cents"] for s in expense["splits"])
        net[payer] += total
        for split in expense["splits"]:
            net[split["user"]] -= split["amount_cents"]

    for settlement in settlements:
        # from_user handed cash to to_user, so from_user's debt shrinks
        # and to_user is owed less than before.
        net[settlement["from_user"]] += settlement["amount_cents"]
        net[settlement["to_user"]] -= settlement["amount_cents"]

    return dict(net)


def simplify_debts(net_cents):
    """
    Turn a {user_id: net_cents} map into a minimal-ish list of transactions
    that settle the group, instead of showing every pairwise expense debt.

    Greedy approach: repeatedly match the biggest creditor against the
    biggest debtor. Not provably minimal in every case, but it's a standard,
    well-understood heuristic and is a large practical improvement over
    "show every pair from every expense" (which is what most naive
    implementations end up doing).
    """
    creditors = [[uid, amt] for uid, amt in net_cents.items() if amt > 0]
    debtors = [[uid, -amt] for uid, amt in net_cents.items() if amt < 0]

    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])

    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt_amt = debtors[i]
        creditor_id, credit_amt = creditors[j]

        pay = min(debt_amt, credit_amt)
        if pay > 0:
            transactions.append(
                {"from_user": debtor_id, "to_user": creditor_id, "amount_cents": pay}
            )

        debtors[i][1] -= pay
        creditors[j][1] -= pay

        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1

    return transactions
