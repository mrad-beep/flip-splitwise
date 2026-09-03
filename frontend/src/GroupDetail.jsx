import { useEffect, useState, useCallback } from "react";
import { api } from "./api.js";

function money(amount) {
  return `₹${amount.toFixed(2)}`;
}

export default function GroupDetail({ group, onGroupChanged, onError }) {
  const [expenses, setExpenses] = useState([]);
  const [balances, setBalances] = useState({ net: [], simplified: [] });
  const [settlements, setSettlements] = useState([]);

  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [paidBy, setPaidBy] = useState(group.members[0]?.id ?? "");
  const [splitAmong, setSplitAmong] = useState(group.members.map((m) => m.id));

  const [settleFrom, setSettleFrom] = useState(group.members[0]?.id ?? "");
  const [settleTo, setSettleTo] = useState(group.members[1]?.id ?? "");
  const [settleAmount, setSettleAmount] = useState("");

  const load = useCallback(async () => {
    try {
      const [e, b, s] = await Promise.all([
        api.listExpenses(group.id),
        api.getBalances(group.id),
        api.listSettlements(group.id),
      ]);
      setExpenses(e);
      setBalances(b);
      setSettlements(s);
    } catch (err) {
      onError(err.message);
    }
  }, [group.id, onError]);

  useEffect(() => {
    load();
    // reset form defaults whenever the selected group changes
    setPaidBy(group.members[0]?.id ?? "");
    setSplitAmong(group.members.map((m) => m.id));
    setSettleFrom(group.members[0]?.id ?? "");
    setSettleTo(group.members[1]?.id ?? "");
  }, [group.id]); // eslint-disable-line react-hooks/exhaustive-deps

  function toggleSplitMember(userId) {
    setSplitAmong((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  }

  async function handleAddExpense(e) {
    e.preventDefault();
    if (!description.trim() || !amount || splitAmong.length === 0) return;
    try {
      await api.addExpense(group.id, {
        description: description.trim(),
        amount: parseFloat(amount),
        paidBy: Number(paidBy),
        splitAmong: splitAmong.map(Number),
      });
      setDescription("");
      setAmount("");
      await load();
    } catch (err) {
      onError(err.message);
    }
  }

  async function handleSettle(e) {
    e.preventDefault();
    if (!settleAmount || settleFrom === settleTo) return;
    try {
      await api.addSettlement(group.id, {
        fromUser: Number(settleFrom),
        toUser: Number(settleTo),
        amount: parseFloat(settleAmount),
      });
      setSettleAmount("");
      await load();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <div className="group-detail">
      <h2>{group.name}</h2>
      <p className="muted">Members: {group.members.map((m) => m.name).join(", ")}</p>

      <div className="grid-2">
        <section className="panel">
          <h3>Add an expense</h3>
          <form onSubmit={handleAddExpense} className="stacked-form">
            <input
              type="text"
              placeholder="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <label className="field-label">
              Paid by
              <select value={paidBy} onChange={(e) => setPaidBy(e.target.value)}>
                {group.members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <div>
              <span className="field-label">Split equally among</span>
              <div className="checkbox-list">
                {group.members.map((m) => (
                  <label key={m.id}>
                    <input
                      type="checkbox"
                      checked={splitAmong.includes(m.id)}
                      onChange={() => toggleSplitMember(m.id)}
                    />
                    {m.name}
                  </label>
                ))}
              </div>
            </div>
            <button type="submit">Add expense</button>
          </form>
        </section>

        <section className="panel">
          <h3>Settle up</h3>
          <form onSubmit={handleSettle} className="stacked-form">
            <label className="field-label">
              From
              <select value={settleFrom} onChange={(e) => setSettleFrom(e.target.value)}>
                {group.members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              To
              <select value={settleTo} onChange={(e) => setSettleTo(e.target.value)}>
                {group.members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              placeholder="Amount"
              value={settleAmount}
              onChange={(e) => setSettleAmount(e.target.value)}
            />
            <button type="submit">Record settlement</button>
          </form>

          <h4>Settlement history</h4>
          <ul className="plain-list">
            {settlements.map((s) => (
              <li key={s.id}>
                {s.from_user.name} &rarr; {s.to_user.name}: {money(s.amount)}
              </li>
            ))}
            {settlements.length === 0 && <li className="muted">None yet</li>}
          </ul>
        </section>
      </div>

      <section className="panel">
        <h3>Balances</h3>
        <div className="grid-2">
          <div>
            <h4>Who's owed / who owes</h4>
            <ul className="plain-list">
              {balances.net.map((n) => (
                <li key={n.user.id}>
                  {n.user.name}:{" "}
                  <span className={n.amount >= 0 ? "positive" : "negative"}>
                    {n.amount >= 0
                      ? `is owed ${money(n.amount)}`
                      : `owes ${money(-n.amount)}`}
                  </span>
                </li>
              ))}
              {balances.net.length === 0 && (
                <li className="muted">Everyone is settled up</li>
              )}
            </ul>
          </div>
          <div>
            <h4>Simplified — who should pay whom</h4>
            <ul className="plain-list">
              {balances.simplified.map((t, i) => (
                <li key={i}>
                  {t.from_user.name} pays {t.to_user.name} {money(t.amount)}
                </li>
              ))}
              {balances.simplified.length === 0 && (
                <li className="muted">Nothing to settle</li>
              )}
            </ul>
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>Expenses</h3>
        <ul className="plain-list">
          {expenses.map((e) => (
            <li key={e.id}>
              <strong>{e.description}</strong> &mdash; {money(e.amount)}, paid by{" "}
              {e.paid_by.name}
              <div className="muted small">
                split:{" "}
                {e.splits.map((s) => `${s.user.name} ${money(s.amount)}`).join(", ")}
              </div>
            </li>
          ))}
          {expenses.length === 0 && <li className="muted">No expenses yet</li>}
        </ul>
      </section>
    </div>
  );
}
