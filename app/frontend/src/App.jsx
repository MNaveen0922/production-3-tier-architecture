import { useState, useEffect } from "react";

// Empty string = relative URL.
// Nginx proxies /auth/* /tickets/* /assign/* to the correct backend.
const API_URL = "";

// ─────────────────────────────────────────────
// Dashboard — shown after login
// ─────────────────────────────────────────────
function Dashboard({ user, onSignOut }) {
  const [tab, setTab] = useState("tickets"); // "tickets" | "mytickets" | "import"
  const [tickets, setTickets] = useState([]);
  const [myTickets, setMyTickets] = useState([]);
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [loadingAssigned, setLoadingAssigned] = useState(false);
  const [msg, setMsg] = useState({ text: "", type: "" });

  const [newTicket, setNewTicket] = useState({ title: "", description: "", priority: "medium" });
  const [importFile, setImportFile] = useState(null);

  useEffect(() => {
    fetchTickets();
  }, []);

  useEffect(() => {
    if (tab === "mytickets") fetchMyTickets();
  }, [tab]);

  async function fetchTickets() {
    setLoadingTickets(true);
    try {
      const res = await fetch(API_URL + "/tickets");
      const data = await res.json();
      setTickets(Array.isArray(data) ? data : []);
    } catch {
      setMsg({ text: "Could not load tickets.", type: "error" });
    } finally {
      setLoadingTickets(false);
    }
  }

  async function fetchMyTickets() {
    setLoadingAssigned(true);
    try {
      const res = await fetch(`${API_URL}/assign/mytickets/${user.id}`);
      const data = await res.json();
      setMyTickets(Array.isArray(data) ? data : []);
    } catch {
      setMsg({ text: "Could not load assigned tickets.", type: "error" });
    } finally {
      setLoadingAssigned(false);
    }
  }

  async function assignTicket(ticketId) {
    setMsg({ text: "", type: "" });
    try {
      const res = await fetch(API_URL + "/assign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id, ticket_id: ticketId }),
      });
      const data = await res.json();
      if (res.status === 201) {
        setMsg({ text: "Ticket assigned to you!", type: "success" });
      } else {
        setMsg({ text: data.detail || "Could not assign ticket.", type: "error" });
      }
    } catch {
      setMsg({ text: "Request failed.", type: "error" });
    }
  }

  async function createTicket(e) {
    e.preventDefault();
    setMsg({ text: "", type: "" });
    try {
      const res = await fetch(API_URL + "/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newTicket),
      });
      const data = await res.json();
      if (res.status === 201) {
        setMsg({ text: "Ticket created!", type: "success" });
        setNewTicket({ title: "", description: "", priority: "medium" });
        fetchTickets();
      } else {
        setMsg({ text: data.detail || "Could not create ticket.", type: "error" });
      }
    } catch {
      setMsg({ text: "Request failed.", type: "error" });
    }
  }

  async function importCsv(e) {
    e.preventDefault();
    if (!importFile) return;
    setMsg({ text: "", type: "" });
    try {
      const form = new FormData();
      form.append("file", importFile);
      const res = await fetch(API_URL + "/tickets/import", { method: "POST", body: form });
      const data = await res.json();
      if (res.status === 202) {
        setMsg({ text: data.message || "Import queued.", type: "success" });
      } else {
        setMsg({ text: data.detail || "Import failed.", type: "error" });
      }
    } catch {
      setMsg({ text: "Request failed.", type: "error" });
    }
  }

  return (
    <div className="dashboard-page">
      {/* ── Top nav ── */}
      <nav className="navbar">
        <div className="nav-brand">
          <div className="brand-mark">🎧</div>
          <span className="brand-name">Support Desk</span>
        </div>
        <div className="nav-user">
          <span>Hi, {user.name}</span>
          <button className="btn-ghost" onClick={onSignOut}>Sign out</button>
        </div>
      </nav>

      <div className="tabs">
        <button className={tab === "tickets" ? "tab active" : "tab"} onClick={() => setTab("tickets")}>
          All Tickets
        </button>
        <button className={tab === "mytickets" ? "tab active" : "tab"} onClick={() => setTab("mytickets")}>
          My Assignments
        </button>
        <button className={tab === "import" ? "tab active" : "tab"} onClick={() => setTab("import")}>
          Bulk Import
        </button>
      </div>

      {msg.text && <div className={`banner ${msg.type}`}>{msg.text}</div>}

      {tab === "tickets" && (
        <div className="panel">
          <form className="ticket-form" onSubmit={createTicket}>
            <h3>Raise a new ticket</h3>
            <input
              placeholder="Title"
              value={newTicket.title}
              onChange={(e) => setNewTicket({ ...newTicket, title: e.target.value })}
              required
            />
            <textarea
              placeholder="Description"
              value={newTicket.description}
              onChange={(e) => setNewTicket({ ...newTicket, description: e.target.value })}
              required
            />
            <select
              value={newTicket.priority}
              onChange={(e) => setNewTicket({ ...newTicket, priority: e.target.value })}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <button type="submit" className="btn-primary">Create Ticket</button>
          </form>

          <h3>Open tickets</h3>
          {loadingTickets ? (
            <p>Loading…</p>
          ) : (
            <div className="card-grid">
              {tickets.map((t) => (
                <div key={t.id} className="ticket-card">
                  <div className={`priority-badge ${t.priority}`}>{t.priority}</div>
                  <h4>{t.title}</h4>
                  <p>{t.description}</p>
                  <button className="btn-secondary" onClick={() => assignTicket(t.id)}>
                    Assign to me
                  </button>
                </div>
              ))}
              {tickets.length === 0 && <p>No tickets yet.</p>}
            </div>
          )}
        </div>
      )}

      {tab === "mytickets" && (
        <div className="panel">
          <h3>Tickets assigned to me</h3>
          {loadingAssigned ? (
            <p>Loading…</p>
          ) : (
            <table className="ticket-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Assigned</th>
                </tr>
              </thead>
              <tbody>
                {myTickets.map((t, i) => (
                  <tr key={i}>
                    <td>{t.title}</td>
                    <td>{t.priority}</td>
                    <td>{t.status}</td>
                    <td>{new Date(t.assigned_date).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!loadingAssigned && myTickets.length === 0 && <p>Nothing assigned to you yet.</p>}
        </div>
      )}

      {tab === "import" && (
        <div className="panel">
          <h3>Bulk import tickets from CSV</h3>
          <p className="hint">Columns: title, description, priority</p>
          <form className="import-form" onSubmit={importCsv}>
            <input type="file" accept=".csv" onChange={(e) => setImportFile(e.target.files[0])} />
            <button type="submit" className="btn-primary">Upload &amp; Queue Import</button>
          </form>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// Auth — sign in / sign up
// ─────────────────────────────────────────────
function AuthPage({ onSignedIn }) {
  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [msg, setMsg] = useState({ text: "", type: "" });
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setMsg({ text: "", type: "" });
    setLoading(true);
    try {
      const path = mode === "signin" ? "/auth/signin" : "/auth/signup";
      const res = await fetch(API_URL + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();

      if (mode === "signin" && res.status === 200) {
        onSignedIn({ id: data.user_id, name: data.name, email: data.email });
      } else if (mode === "signup" && res.status === 201) {
        setMsg({ text: "Account created — please sign in.", type: "success" });
        setMode("signin");
      } else {
        setMsg({ text: data.detail || "Something went wrong.", type: "error" });
      }
    } catch {
      setMsg({ text: "Request failed.", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand-mark large">🎧</div>
        <h1>Support Desk</h1>
        <p className="subtitle">IT helpdesk ticketing, assignment &amp; notifications</p>

        <div className="auth-toggle">
          <button className={mode === "signin" ? "active" : ""} onClick={() => setMode("signin")}>
            Sign In
          </button>
          <button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>
            Sign Up
          </button>
        </div>

        <form onSubmit={submit}>
          {mode === "signup" && (
            <input
              placeholder="Full name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          )}
          <input
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Please wait…" : mode === "signin" ? "Sign In" : "Create Account"}
          </button>
        </form>

        {msg.text && <div className={`banner ${msg.type}`}>{msg.text}</div>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Root component
// ─────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(null);

  if (!user) {
    return <AuthPage onSignedIn={setUser} />;
  }

  return <Dashboard user={user} onSignOut={() => setUser(null)} />;
}
