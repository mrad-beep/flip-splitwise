import { useEffect, useState, useCallback } from "react";
import { api } from "./api.js";
import GroupDetail from "./GroupDetail.jsx";

export default function App() {
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState(null);

  const [newUserName, setNewUserName] = useState("");
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupMembers, setNewGroupMembers] = useState([]);

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [u, g] = await Promise.all([api.listUsers(), api.listGroups()]);
      setUsers(u);
      setGroups(g);
    } catch (e) {
      setError(
        `Could not reach the backend at http://localhost:5000. Is it running? (${e.message})`
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleCreateUser(e) {
    e.preventDefault();
    if (!newUserName.trim()) return;
    try {
      await api.createUser(newUserName.trim());
      setNewUserName("");
      await refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleCreateGroup(e) {
    e.preventDefault();
    if (!newGroupName.trim() || newGroupMembers.length === 0) return;
    try {
      const group = await api.createGroup(newGroupName.trim(), newGroupMembers);
      setNewGroupName("");
      setNewGroupMembers([]);
      await refresh();
      setSelectedGroupId(group.id);
    } catch (e) {
      setError(e.message);
    }
  }

  function toggleMember(userId) {
    setNewGroupMembers((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  }

  const selectedGroup = groups.find((g) => g.id === selectedGroupId);

  return (
    <div className="app">
      <header>
        <h1>Splitwise (mini)</h1>
        <p className="subtitle">Flip Retail assignment &mdash; Part B</p>
      </header>

      {error && (
        <div className="banner error">
          {error}
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      {loading ? (
        <p>Loading&hellip;</p>
      ) : (
        <div className="layout">
          <aside className="sidebar">
            <section className="panel">
              <h2>People</h2>
              <ul className="plain-list">
                {users.map((u) => (
                  <li key={u.id}>{u.name}</li>
                ))}
                {users.length === 0 && <li className="muted">No people yet</li>}
              </ul>
              <form onSubmit={handleCreateUser} className="inline-form">
                <input
                  type="text"
                  placeholder="Add a person"
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                />
                <button type="submit">Add</button>
              </form>
            </section>

            <section className="panel">
              <h2>Groups</h2>
              <ul className="plain-list">
                {groups.map((g) => (
                  <li key={g.id}>
                    <button
                      className={
                        "group-link" + (g.id === selectedGroupId ? " active" : "")
                      }
                      onClick={() => setSelectedGroupId(g.id)}
                    >
                      {g.name}{" "}
                      <span className="muted">({g.members.length} people)</span>
                    </button>
                  </li>
                ))}
                {groups.length === 0 && <li className="muted">No groups yet</li>}
              </ul>

              <form onSubmit={handleCreateGroup} className="stacked-form">
                <input
                  type="text"
                  placeholder="Group name"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                />
                <div className="checkbox-list">
                  {users.map((u) => (
                    <label key={u.id}>
                      <input
                        type="checkbox"
                        checked={newGroupMembers.includes(u.id)}
                        onChange={() => toggleMember(u.id)}
                      />
                      {u.name}
                    </label>
                  ))}
                </div>
                <button type="submit">Create group</button>
              </form>
            </section>
          </aside>

          <main className="content">
            {selectedGroup ? (
              <GroupDetail
                group={selectedGroup}
                onGroupChanged={refresh}
                onError={setError}
              />
            ) : (
              <p className="muted">Select or create a group to get started.</p>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
