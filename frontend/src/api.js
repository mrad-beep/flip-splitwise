const BASE_URL = "http://localhost:5000/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let body = null;
  try {
    body = await res.json();
  } catch {
    // no JSON body (e.g. network error before the server responded)
  }

  if (!res.ok) {
    const message = body?.error || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return body;
}

export const api = {
  listUsers: () => request("/users"),
  createUser: (name) =>
    request("/users", { method: "POST", body: JSON.stringify({ name }) }),

  listGroups: () => request("/groups"),
  createGroup: (name, memberIds) =>
    request("/groups", {
      method: "POST",
      body: JSON.stringify({ name, member_ids: memberIds }),
    }),
  getGroup: (groupId) => request(`/groups/${groupId}`),
  addMember: (groupId, userId) =>
    request(`/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),

  listExpenses: (groupId) => request(`/groups/${groupId}/expenses`),
  addExpense: (groupId, { description, amount, paidBy, splitAmong }) =>
    request(`/groups/${groupId}/expenses`, {
      method: "POST",
      body: JSON.stringify({
        description,
        amount,
        paid_by: paidBy,
        split_among: splitAmong,
      }),
    }),

  getBalances: (groupId) => request(`/groups/${groupId}/balances`),

  listSettlements: (groupId) => request(`/groups/${groupId}/settlements`),
  addSettlement: (groupId, { fromUser, toUser, amount }) =>
    request(`/groups/${groupId}/settlements`, {
      method: "POST",
      body: JSON.stringify({ from_user: fromUser, to_user: toUser, amount }),
    }),
};
