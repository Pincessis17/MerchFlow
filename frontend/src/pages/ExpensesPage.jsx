import { useEffect, useState } from "react"
import { useOutletContext } from "react-router-dom"

import api from "../lib/api"

const emptyForm = { category: "", amount: "", description: "" }

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

export default function ExpensesPage() {
  const { selectedBusinessId } = useOutletContext()
  const [expenses, setExpenses] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function loadExpenses() {
    if (!selectedBusinessId) {
      setExpenses([])
      return
    }

    setLoading(true)
    setError("")
    try {
      const { data } = await api.get("expenses/", {
        params: { business: selectedBusinessId },
      })
      setExpenses(data)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadExpenses()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBusinessId])

  async function handleSubmit(event) {
    event.preventDefault()
    setMessage("")

    if (!selectedBusinessId) {
      setMessage("Select a business first.")
      return
    }

    const payload = {
      business: selectedBusinessId,
      category: form.category,
      amount: Number(form.amount || 0),
      description: form.description,
    }

    try {
      if (editingId) {
        await api.patch(`expenses/${editingId}/`, payload)
        setMessage("Expense updated.")
      } else {
        await api.post("expenses/", payload)
        setMessage("Expense added.")
      }
      setEditingId(null)
      setForm(emptyForm)
      await loadExpenses()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Save failed.")
    }
  }

  function handleEdit(expense) {
    setEditingId(expense.id)
    setForm({
      category: expense.category || "",
      amount: expense.amount || "",
      description: expense.description || "",
    })
  }

  async function handleDelete(expenseId) {
    try {
      await api.delete(`expenses/${expenseId}/`)
      setMessage("Expense deleted.")
      if (editingId === expenseId) {
        setEditingId(null)
        setForm(emptyForm)
      }
      await loadExpenses()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Delete failed.")
    }
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Expenses</div>
          <div className="section-sub">Track business expenses</div>
        </div>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading expenses...</div> : null}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><div className="card-title">{editingId ? "Edit Expense" : "Add Expense"}</div></div>
        <div className="card-body">
          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-row cols-2">
              <div className="form-group">
                <label>Category</label>
                <input value={form.category} onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value }))} required />
              </div>
              <div className="form-group">
                <label>Amount</label>
                <input type="number" step="0.01" min="0" value={form.amount} onChange={(event) => setForm((prev) => ({ ...prev, amount: event.target.value }))} required />
              </div>
            </div>
            <div className="form-row" style={{ marginBottom: 8 }}>
              <div className="form-group">
                <label>Description</label>
                <input value={form.description} onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))} />
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="btn btn-primary">{editingId ? "Update Expense" : "Add Expense"}</button>
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
                <th>Category</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {expenses.length === 0 ? <EmptyRow cols={5} text="No expenses found" /> : expenses.map((expense) => (
                <tr key={expense.id}>
                  <td className="td-main">{expense.category}</td>
                  <td>{expense.description || "-"}</td>
                  <td>${Number(expense.amount).toFixed(2)}</td>
                  <td>{new Date(expense.created_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button type="button" className="btn btn-ghost" onClick={() => handleEdit(expense)}>Edit</button>
                      <button type="button" className="btn btn-ghost" onClick={() => handleDelete(expense.id)}>Delete</button>
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
