from flask import Blueprint, request, jsonify
from .extensions import db
from .models import User, Group, Expense, ExpenseSplit, Settlement
from .balances import equal_split_cents, compute_net_balances, simplify_debts

api_bp = Blueprint("api", __name__)


def to_cents(amount):
    """Turn a request's float/str amount into integer cents, rejecting junk input."""
    try:
        return round(float(amount) * 100)
    except (TypeError, ValueError):
        return None


def error(message, status=400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------- Users ----

@api_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return error("name is required")

    user = User(name=name)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@api_bp.route("/users", methods=["GET"])
def list_users():
    users = User.query.order_by(User.id).all()
    return jsonify([u.to_dict() for u in users])


# --------------------------------------------------------------- Groups ----

@api_bp.route("/groups", methods=["POST"])
def create_group():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    member_ids = data.get("member_ids") or []

    if not name:
        return error("name is required")

    members = User.query.filter(User.id.in_(member_ids)).all()
    if len(members) != len(set(member_ids)):
        return error("one or more member_ids do not exist")

    group = Group(name=name, members=members)
    db.session.add(group)
    db.session.commit()
    return jsonify(group.to_dict()), 201


@api_bp.route("/groups", methods=["GET"])
def list_groups():
    groups = Group.query.order_by(Group.id).all()
    return jsonify([g.to_dict() for g in groups])


@api_bp.route("/groups/<int:group_id>", methods=["GET"])
def get_group(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return error("group not found", 404)
    return jsonify(group.to_dict())


@api_bp.route("/groups/<int:group_id>/members", methods=["POST"])
def add_member(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return error("group not found", 404)

    data = request.get_json(silent=True) or {}
    user = db.session.get(User, data.get("user_id"))
    if not user:
        return error("user not found", 404)

    if user not in group.members:
        group.members.append(user)
        db.session.commit()
    return jsonify(group.to_dict()), 201


# ------------------------------------------------------------- Expenses ----

@api_bp.route("/groups/<int:group_id>/expenses", methods=["POST"])
def add_expense(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return error("group not found", 404)

    data = request.get_json(silent=True) or {}
    description = (data.get("description") or "").strip()
    paid_by_id = data.get("paid_by")
    split_among = data.get("split_among")  # list of user ids, optional

    amount_cents = to_cents(data.get("amount"))
    if not description:
        return error("description is required")
    if amount_cents is None or amount_cents <= 0:
        return error("amount must be a positive number")

    member_ids = {m.id for m in group.members}
    payer = db.session.get(User, paid_by_id)
    if not payer or payer.id not in member_ids:
        return error("paid_by must be a member of this group")

    if split_among is None:
        split_among = list(member_ids)
    if not split_among:
        return error("split_among cannot be empty")
    if not set(split_among).issubset(member_ids):
        return error("split_among must only contain members of this group")

    shares = equal_split_cents(amount_cents, split_among)

    expense = Expense(
        group_id=group.id,
        description=description,
        amount_cents=amount_cents,
        paid_by_id=payer.id,
    )
    expense.splits = [
        ExpenseSplit(user_id=uid, amount_cents=cents) for uid, cents in shares.items()
    ]
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201


@api_bp.route("/groups/<int:group_id>/expenses", methods=["GET"])
def list_expenses(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return error("group not found", 404)
    expenses = (
        Expense.query.filter_by(group_id=group_id)
        .order_by(Expense.created_at.desc())
        .all()
    )
    return jsonify([e.to_dict() for e in expenses])


# ----------------------------------------------------------- Balances -----

@api_bp.route("/groups/<int:group_id>/balances", methods=["GET"])
def get_balances(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return error("group not found", 404)

    expenses = [
        {
            "paid_by": e.paid_by_id,
            "splits": [{"user": s.user_id, "amount_cents": s.amount_cents} for s in e.splits],
        }
        for e in group.expenses
    ]
    settlements = [
        {
            "from_user": s.from_user_id,
            "to_user": s.to_user_id,
            "amount_cents": s.amount_cents,
        }
        for s in group.settlements
    ]

    net_cents = compute_net_balances(expenses, settlements)
    users_by_id = {u.id: u for u in group.members}

    net = [
        {"user": users_by_id[uid].to_dict(), "amount": cents / 100}
        for uid, cents in net_cents.items()
        if uid in users_by_id and cents != 0
    ]

    simplified_raw = simplify_debts(net_cents)
    simplified = [
        {
            "from_user": users_by_id[t["from_user"]].to_dict(),
            "to_user": users_by_id[t["to_user"]].to_dict(),
            "amount": t["amount_cents"] / 100,
        }
        for t in simplified_raw
        if t["from_user"] in users_by_id and t["to_user"] in users_by_id
    ]

    return jsonify({"net": net, "simplified": simplified})


# --------------------------------------------------------- Settlements ----

@api_bp.route("/groups/<int:group_id>/settlements", methods=["POST"])
def add_settlement(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return error("group not found", 404)

    data = request.get_json(silent=True) or {}
    from_id = data.get("from_user")
    to_id = data.get("to_user")
    amount_cents = to_cents(data.get("amount"))

    member_ids = {m.id for m in group.members}
    if from_id not in member_ids or to_id not in member_ids:
        return error("from_user and to_user must be members of this group")
    if from_id == to_id:
        return error("from_user and to_user must be different")
    if amount_cents is None or amount_cents <= 0:
        return error("amount must be a positive number")

    settlement = Settlement(
        group_id=group.id,
        from_user_id=from_id,
        to_user_id=to_id,
        amount_cents=amount_cents,
    )
    db.session.add(settlement)
    db.session.commit()
    return jsonify(settlement.to_dict()), 201


@api_bp.route("/groups/<int:group_id>/settlements", methods=["GET"])
def list_settlements(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return error("group not found", 404)
    settlements = (
        Settlement.query.filter_by(group_id=group_id)
        .order_by(Settlement.created_at.desc())
        .all()
    )
    return jsonify([s.to_dict() for s in settlements])
