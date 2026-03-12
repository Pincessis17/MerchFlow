import { useEffect, useState } from "react"
import { useOutletContext } from "react-router-dom"

import api from "../lib/api"

const emptyForm = { name: "", email: "", phone: "" }

function EmptyRow({ cols, text }) {
  return (
    <tr>
      <td colSpan={cols}>
        <div className="empty">
          <div className="empty-title">{text}</div>
        </div>
      </td>
    </tr>
  )
}

export default function CustomersPage() {
  const { selectedBusinessId } = useOutletContext()
  const [customers, setCustomers] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function loadCustomers() {
    if (!selectedBusinessId) {
      setCustomers([])
      return
    }

    setLoading(true)
    setError("")
    try {
      const { data } = await api.get("customers/", {
        params: { business: selectedBusinessId },
      })
      setCustomers(data)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCustomers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBusinessId])

  async function handleSubmit(event) {
    event.preventDefault()
    setMessage("")

    if (!selectedBusinessId) {
      setMessage("Select a business first.")
      return
    }

    try {
      const payload = {
        business: selectedBusinessId,
        name: form.name,
        email: form.email,
        phone: form.phone,
      }

      if (editingId) {
        await api.patch(`customers/${editingId}/`, payload)
        setMessage("Customer updated.")
      } else {
        await api.post("customers/", payload)
        setMessage("Customer added.")
      }

      setForm(emptyForm)
      setEditingId(null)
      await loadCustomers()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Save failed.")
    }
  }

  function handleEdit(customer) {
    setEditingId(customer.id)
    setForm({
      name: customer.name || "",
      email: customer.email || "",
      phone: customer.phone || "",
    })
  }

  async function handleDelete(customerId) {
    try {
      await api.delete(`customers/${customerId}/`)
      setMessage("Customer deleted.")
      if (editingId === customerId) {
        setEditingId(null)
        setForm(emptyForm)
      }
      await loadCustomers()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Delete failed.")
    }
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Customers</div>
          <div className="section-sub">Customer database</div>
        </div>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading customers...</div> : null}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div className="card-title">{editingId ? "Edit Customer" : "Add Customer"}</div>
        </div>
        <div className="card-body">
          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-row cols-2">
              <div className="form-group">
                <label>Name</label>
                <input value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} required />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} />
              </div>
            </div>
            <div className="form-row" style={{ marginBottom: 8 }}>
              <div className="form-group">
                <label>Phone</label>
                <input value={form.phone} onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))} />
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="btn btn-primary">{editingId ? "Update Customer" : "Add Customer"}</button>
              {editingId ? <button type="button" className="btn btn-ghost" onClick={() => { setEditingId(null); setForm(emptyForm) }}>Cancel</button> : null}
            </div>
          </form>
          {message ? <div className="alert-strip" style={{ marginTop: 10 }}>{message}</div> : null}
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.length === 0 ? <EmptyRow cols={4} text="No customers found" /> : customers.map((customer) => (
                <tr key={customer.id}>
                  <td className="td-main">{customer.name}</td>
                  <td>{customer.email || "-"}</td>
                  <td>{customer.phone || "-"}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button type="button" className="btn btn-ghost" onClick={() => handleEdit(customer)}>Edit</button>
                      <button type="button" className="btn btn-ghost" onClick={() => handleDelete(customer.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
