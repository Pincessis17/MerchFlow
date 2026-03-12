import { useMemo, useState } from "react"
import { useNavigate, useOutletContext } from "react-router-dom"

import api from "../lib/api"

const emptyForm = {
  name: "",
  email: "",
  phone: "",
  address: "",
  ownerEmail: "",
  ownerPassword: "",
}

export default function ConsoleTenantsPage() {
  const navigate = useNavigate()
  const { businesses, users, reload } = useOutletContext()
  const [query, setQuery] = useState("")
  const [message, setMessage] = useState("")
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    if (!q) return businesses
    return businesses.filter((business) =>
      business.name.toLowerCase().includes(q) ||
      (business.email || "").toLowerCase().includes(q),
    )
  }, [businesses, query])

  function startEdit(business) {
    setEditingId(business.id)
    setForm({
      name: business.name || "",
      email: business.email || "",
      phone: business.phone || "",
      address: business.address || "",
      ownerEmail: "",
      ownerPassword: "",
    })
  }

  async function handleSaveTenant(event) {
    event.preventDefault()
    setMessage("")
    try {
      if (editingId) {
        await api.patch(`businesses/${editingId}/`, {
          name: form.name,
          email: form.email,
          phone: form.phone,
          address: form.address,
        })
        setMessage("Tenant updated.")
      } else {
        const businessRes = await api.post("businesses/", {
          name: form.name,
          email: form.email,
          phone: form.phone,
          address: form.address,
        })
        await api.post("users/", {
          email: form.ownerEmail,
          password: form.ownerPassword,
          role: "owner",
          business: businessRes.data.id,
        })
        setMessage("Tenant created.")
      }
      setForm(emptyForm)
      setEditingId(null)
      await reload()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Save failed.")
    }
  }

  async function handleDeleteTenant(businessId) {
    try {
      await api.delete(`businesses/${businessId}/`)
      setMessage("Tenant deleted.")
      await reload()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Delete failed.")
    }
  }

  function handleLoginAs(businessId) {
    localStorage.setItem("selected_business_id", String(businessId))
    navigate("/dashboard")
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Tenants</div>
          <div className="section-sub">Companies subscribed to MerchFlow</div>
        </div>
        <input placeholder="Search tenants..." value={query} onChange={(event) => setQuery(event.target.value)} style={{ width: 220 }} />
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><div className="card-title">{editingId ? "Edit Tenant" : "Add Tenant"}</div></div>
        <div className="card-body">
          <form className="auth-form" onSubmit={handleSaveTenant}>
            <div className="form-row cols-2">
              <div className="form-group"><label>Company Name</label><input required value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} /></div>
              <div className="form-group"><label>Company Email</label><input value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} /></div>
            </div>
            <div className="form-row cols-2">
              <div className="form-group"><label>Phone</label><input value={form.phone} onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))} /></div>
              <div className="form-group"><label>Address</label><input value={form.address} onChange={(event) => setForm((prev) => ({ ...prev, address: event.target.value }))} /></div>
            </div>
            {!editingId ? (
              <div className="form-row cols-2">
                <div className="form-group"><label>Owner Email</label><input required type="email" value={form.ownerEmail} onChange={(event) => setForm((prev) => ({ ...prev, ownerEmail: event.target.value }))} /></div>
                <div className="form-group"><label>Owner Password</label><input required type="password" value={form.ownerPassword} onChange={(event) => setForm((prev) => ({ ...prev, ownerPassword: event.target.value }))} /></div>
              </div>
            ) : null}
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="btn btn-primary">{editingId ? "Update Tenant" : "Add Tenant"}</button>
              {editingId ? <button type="button" className="btn btn-ghost" onClick={() => { setEditingId(null); setForm(emptyForm) }}>Cancel</button> : null}
            </div>
          </form>
          {message ? <div className="alert-strip" style={{ marginTop: 10 }}>{message}</div> : null}
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Company</th><th>Email</th><th>Users</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>
              {filtered.map((business) => {
                const userCount = users.filter((user) => user.business === business.id).length
                return (
                  <tr key={business.id}>
                    <td className="td-main">{business.name}</td>
                    <td>{business.email || "-"}</td>
                    <td>{userCount}</td>
                    <td>{new Date(business.created_at).toLocaleDateString()}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button type="button" className="btn btn-ghost" onClick={() => startEdit(business)}>Manage</button>
                        <button type="button" className="btn btn-ghost" onClick={() => handleLoginAs(business.id)}>Login As</button>
                        <button type="button" className="btn btn-ghost" onClick={() => handleDeleteTenant(business.id)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
