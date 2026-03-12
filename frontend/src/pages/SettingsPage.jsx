import { useEffect, useState } from "react"
import { useOutletContext } from "react-router-dom"

import api from "../lib/api"

const emptyStaffForm = {
  full_name: "",
  email: "",
  role: "staff",
  password: "",
  confirm_password: "",
}

function roleBadge(role) {
  if (role === "owner") return "badge badge-blue"
  if (role === "manager") return "badge badge-yellow"
  return "badge badge-green"
}

export default function SettingsPage() {
  const { selectedBusinessId } = useOutletContext()
  const [users, setUsers] = useState([])
  const [form, setForm] = useState(emptyStaffForm)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function loadUsers() {
    if (!selectedBusinessId) {
      setUsers([])
      return
    }

    setLoading(true)
    setError("")
    try {
      const { data } = await api.get("users/")
      setUsers(data.filter((user) => user.business === selectedBusinessId))
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBusinessId])

  async function handleCreateUser(event) {
    event.preventDefault()
    setMessage("")

    if (form.password !== form.confirm_password) {
      setMessage("Password confirmation does not match.")
      return
    }

    try {
      await api.post("users/", {
        email: form.email,
        password: form.password,
        role: form.role,
        business: selectedBusinessId,
      })
      setForm(emptyStaffForm)
      setMessage("Staff member created.")
      await loadUsers()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Failed to create user.")
    }
  }

  async function handleDeleteUser(userId) {
    try {
      await api.delete(`users/${userId}/`)
      setMessage("User removed.")
      await loadUsers()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Failed to remove user.")
    }
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Team & Access</div>
          <div className="section-sub">Manage staff logins and permissions</div>
        </div>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading team members...</div> : null}

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><div className="card-title">Add Staff Member</div></div>
          <div className="card-body">
            <form className="auth-form" onSubmit={handleCreateUser}>
              <label>Full Name</label>
              <input value={form.full_name} onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))} placeholder="Staff name" />

              <label>Email Address</label>
              <input type="email" required value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} placeholder="staff@company.com" />

              <label>Role</label>
              <select value={form.role} onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value }))}>
                <option value="staff">Staff</option>
                <option value="manager">Manager</option>
                <option value="owner">Admin</option>
              </select>

              <div className="form-row cols-2" style={{ marginBottom: 8 }}>
                <div className="form-group">
                  <label>Temp Password</label>
                  <input type="password" required value={form.password} onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Confirm</label>
                  <input type="password" required value={form.confirm_password} onChange={(event) => setForm((prev) => ({ ...prev, confirm_password: event.target.value }))} />
                </div>
              </div>

              <button type="submit" className="btn btn-primary">Create User</button>
            </form>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">Team Members</div></div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Access</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr><td colSpan={4}><div className="empty"><div className="empty-title">No team members yet</div></div></td></tr>
                ) : users.map((user) => (
                  <tr key={user.id}>
                    <td className="td-main">{user.email.split("@")[0]}</td>
                    <td><span className={roleBadge(user.role)}>{user.role}</span></td>
                    <td><span className="badge badge-green">Full</span></td>
                    <td><button type="button" className="btn btn-ghost" onClick={() => handleDeleteUser(user.id)}>Remove</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card-body" style={{ paddingTop: 12 }}>
            <div className="alert-strip">i Staff members sign in from the regular login page</div>
          </div>
        </div>
      </div>

      {message ? <div className="alert-strip" style={{ marginTop: 16 }}>{message}</div> : null}
    </>
  )
}
