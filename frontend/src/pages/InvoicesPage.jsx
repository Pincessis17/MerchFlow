import { useEffect, useState } from "react"
import { useOutletContext } from "react-router-dom"

import api from "../lib/api"

const emptyForm = {
  sale: "",
  invoice_number: "",
  amount_paid: "0",
  status: "pending",
}

function badgeClass(status) {
  if (status === "paid" || status === "active") return "badge badge-green"
  if (status === "pending" || status === "trial") return "badge badge-yellow"
  if (status === "cancelled") return "badge badge-red"
  return "badge badge-gray"
}

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

export default function InvoicesPage() {
  const { selectedBusinessId } = useOutletContext()
  const [invoices, setInvoices] = useState([])
  const [sales, setSales] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function loadData() {
    if (!selectedBusinessId) {
      setInvoices([])
      setSales([])
      return
    }

    setLoading(true)
    setError("")
    try {
      const params = { business: selectedBusinessId }
      const [invoicesRes, salesRes] = await Promise.all([
        api.get("invoices/", { params }),
        api.get("sales/", { params }),
      ])
      setInvoices(invoicesRes.data)
      setSales(salesRes.data)
      if (!form.sale && salesRes.data.length > 0) {
        setForm((prev) => ({ ...prev, sale: String(salesRes.data[0].id) }))
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBusinessId])

  async function handleSubmit(event) {
    event.preventDefault()
    setMessage("")

    if (!form.sale) {
      setMessage("Choose a sale first.")
      return
    }

    const payload = {
      sale: Number(form.sale),
      invoice_number: form.invoice_number,
      amount_paid: Number(form.amount_paid || 0),
      status: form.status,
    }

    try {
      if (editingId) {
        await api.patch(`invoices/${editingId}/`, payload)
        setMessage("Invoice updated.")
      } else {
        await api.post("invoices/", payload)
        setMessage("Invoice created.")
      }
      setForm(emptyForm)
      setEditingId(null)
      await loadData()
    } catch (err) {
      const detail = err?.response?.data
      if (detail && typeof detail === "object") {
        const first = Object.values(detail).flat()[0]
        setMessage(String(first || "Save failed."))
      } else {
        setMessage(err?.message || "Save failed.")
      }
    }
  }

  function handleEdit(invoice) {
    setEditingId(invoice.id)
    setForm({
      sale: String(invoice.sale || ""),
      invoice_number: invoice.invoice_number || "",
      amount_paid: String(invoice.amount_paid ?? "0"),
      status: invoice.status || "pending",
    })
  }

  async function handleDelete(invoiceId) {
    try {
      await api.delete(`invoices/${invoiceId}/`)
      setMessage("Invoice deleted.")
      if (editingId === invoiceId) {
        setEditingId(null)
        setForm(emptyForm)
      }
      await loadData()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Delete failed.")
    }
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Invoices</div>
          <div className="section-sub">Generate and manage invoices</div>
        </div>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading invoices...</div> : null}

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><div className="card-title">{editingId ? "Edit Invoice" : "Create Invoice"}</div></div>
        <div className="card-body">
          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="form-row cols-2">
              <div className="form-group">
                <label>Sale</label>
                <select value={form.sale} onChange={(event) => setForm((prev) => ({ ...prev, sale: event.target.value }))} required>
                  {sales.map((sale) => (
                    <option key={sale.id} value={sale.id}>Sale #{sale.id} - ${Number(sale.total).toFixed(2)}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Invoice Number</label>
                <input value={form.invoice_number} onChange={(event) => setForm((prev) => ({ ...prev, invoice_number: event.target.value }))} required />
              </div>
            </div>
            <div className="form-row cols-2" style={{ marginBottom: 8 }}>
              <div className="form-group">
                <label>Amount Paid</label>
                <input type="number" step="0.01" min="0" value={form.amount_paid} onChange={(event) => setForm((prev) => ({ ...prev, amount_paid: event.target.value }))} />
              </div>
              <div className="form-group">
                <label>Status</label>
                <select value={form.status} onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value }))}>
                  <option value="draft">draft</option>
                  <option value="pending">pending</option>
                  <option value="paid">paid</option>
                </select>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" className="btn btn-primary">{editingId ? "Update Invoice" : "Create Invoice"}</button>
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
                <th>Invoice</th>
                <th>Sale</th>
                <th>Status</th>
                <th>Paid</th>
                <th>Total</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.length === 0 ? <EmptyRow cols={7} text="No invoices found" /> : invoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td className="td-main">{invoice.invoice_number}</td>
                  <td>#{invoice.sale}</td>
                  <td><span className={badgeClass(invoice.status)}>{invoice.status}</span></td>
                  <td>${Number(invoice.amount_paid).toFixed(2)}</td>
                  <td>${Number(invoice.total || 0).toFixed(2)}</td>
                  <td>{new Date(invoice.created_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button type="button" className="btn btn-ghost" onClick={() => handleEdit(invoice)}>Edit</button>
                      <button type="button" className="btn btn-ghost" onClick={() => handleDelete(invoice.id)}>Delete</button>
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
