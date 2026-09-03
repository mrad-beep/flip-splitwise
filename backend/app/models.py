from datetime import datetime, timezone
from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# Many-to-many: which users belong to which groups.
group_members = db.Table(
    "group_members",
    db.Column("group_id", db.Integer, db.ForeignKey("group.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    members = db.relationship("User", secondary=group_members, lazy="subquery")
    expenses = db.relationship(
        "Expense", backref="group", lazy=True, cascade="all, delete-orphan"
    )
    settlements = db.relationship(
        "Settlement", backref="group", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "members": [m.to_dict() for m in self.members],
        }


class Expense(db.Model):
    """
    One expense = one payment event. We do NOT store "amount / n" as a single
    number anywhere — every person's share is its own ExpenseSplit row, in
    integer cents. That's deliberate: it's the only representation that (a)
    still works once splits stop being equal, (b) can never silently drift
    from the expense total due to float rounding, and (c) lets balance
    calculation be a single pass over rows instead of re-deriving splits.
    """

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    paid_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    paid_by = db.relationship("User", foreign_keys=[paid_by_id])
    splits = db.relationship(
        "ExpenseSplit", backref="expense", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "description": self.description,
            "amount": self.amount_cents / 100,
            "paid_by": self.paid_by.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "splits": [s.to_dict() for s in self.splits],
        }


class ExpenseSplit(db.Model):
    """How much one specific user owes for one specific expense."""

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expense.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "user": self.user.to_dict(),
            "amount": self.amount_cents / 100,
        }


class Settlement(db.Model):
    """A record of one person paying another back, outside of any expense."""

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    from_user = db.relationship("User", foreign_keys=[from_user_id])
    to_user = db.relationship("User", foreign_keys=[to_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "from_user": self.from_user.to_dict(),
            "to_user": self.to_user.to_dict(),
            "amount": self.amount_cents / 100,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
