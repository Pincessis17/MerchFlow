import { useEffect, useMemo, useState } from "react"
import { useOutletContext } from "react-router-dom"

import api from "../lib/api"

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

function newItem(products) {
  return {
    productId: products.length ? String(products[0].id) : "",
    quantity: "1",
  }
}

export default function SalesPage() {
  const { selectedBusinessId } = useOutletContext()
  const [sales, setSales] = useState([])
  const [products, setProducts] = useState([])
  const [customers, setCustomers] = useState([])

  const [customerId, setCustomerId] = useState("")
  const [saleDate, setSaleDate] = useState("")
  const [paymentMethod, setPaymentMethod] = useState("cash")
  const [notes, setNotes] = useState("")
  const [items, setItems] = useState([])

  const [saveMessage, setSaveMessage] = useState("")
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    async function loadSalesPageData() {
      if (!selectedBusinessId) {
        setSales([])
        setProducts([])
        setCustomers([])
        setItems([])
        return
      }

      setLoading(true)
      setError("")
      try {
        const params = { business: selectedBusinessId }
        const [salesRes, productsRes, customersRes] = await Promise.all([
          api.get("sales/", { params }),
          api.get("products/", { params }),
          api.get("customers/", { params }),
        ])
        setSales(salesRes.data)
        setProducts(productsRes.data)
        setCustomers(customersRes.data)
        if (productsRes.data.length > 0) {
          setItems([newItem(productsRes.data)])
        }
      } catch (err) {
        setError(err?.response?.data?.detail || err.message)
      } finally {
        setLoading(false)
      }
    }

    loadSalesPageData()
  }, [selectedBusinessId])

  const computed = useMemo(() => {
    let subtotal = 0
    for (const item of items) {
      const product = products.find((p) => p.id === Number(item.productId))
      const unitPrice = Number(product?.selling_price || 0)
      subtotal += unitPrice * Number(item.quantity || 0)
    }
    const tax = subtotal * 0.15
    const total = subtotal + tax
    return { subtotal, tax, total }
  }, [items, products])

  function addItem() {
    setItems((prev) => [...prev, newItem(products)])
  }

  function updateItem(index, patch) {
    setItems((prev) => prev.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)))
  }

  function removeItem(index) {
    setItems((prev) => prev.filter((_, itemIndex) => itemIndex !== index))
  }

  async function submitSale({ createInvoice }) {
    setSaveMessage("")
    setSaving(true)
    try {
      if (!selectedBusinessId) throw new Error("Select a business first.")
      if (items.length === 0) throw new Error("Add at least one line item.")

      const payloadItems = items.map((item) => {
        const product = products.find((p) => p.id === Number(item.productId))
        const quantity = Number(item.quantity || 0)
        const unitPrice = Number(product?.selling_price || 0)
        return {
          product: Number(item.productId),
          quantity,
          unit_price: unitPrice,
          line_total: unitPrice * quantity,
        }
      })

      const saleRes = await api.post("sales/", {
        business: selectedBusinessId,
        customer: customerId ? Number(customerId) : null,
        items: payloadItems,
      })

      if (createInvoice) {
        const invoiceNumber = `INV-${saleRes.data.id}-${Date.now().toString().slice(-4)}`
        await api.post("invoices/", {
          sale: saleRes.data.id,
          invoice_number: invoiceNumber,
          amount_paid: 0,
          status: "pending",
        })
      }

      const salesRes = await api.get("sales/", { params: { business: selectedBusinessId } })
      setSales(salesRes.data)
      setItems([newItem(products)])
      setCustomerId("")
      setNotes("")
      setSaveMessage(createInvoice ? "Sale and invoice created." : "Sale saved.")
    } catch (err) {
      setSaveMessage(err?.response?.data?.detail || err.message || "Save failed.")
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteSale(saleId) {
    setSaveMessage("")
    try {
      await api.delete(`sales/${saleId}/`)
      setSaveMessage("Sale deleted.")
      const { data } = await api.get("sales/", { params: { business: selectedBusinessId } })
      setSales(data)
    } catch (err) {
      setSaveMessage(err?.response?.data?.detail || err.message || "Failed to delete sale.")
    }
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Create New Sale</div>
          <div className="section-sub">Record a transaction and generate an invoice</div>
        </div>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading sales...</div> : null}

      <div className="grid-2" style={{ alignItems: "start" }}>
        <div>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header"><div className="card-title">Customer</div></div>
            <div className="card-body">
              <div className="form-row cols-2" style={{ marginBottom: 0 }}>
                <div className="form-group">
                  <label>Select Customer</label>
                  <select value={customerId} onChange={(event) => setCustomerId(event.target.value)}>
                    <option value="">Search customer...</option>
                    {customers.map((customer) => (
                      <option key={customer.id} value={customer.id}>{customer.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Sale Date</label>
                  <input type="date" value={saleDate} onChange={(event) => setSaleDate(event.target.value)} />
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div className="card-title">Line Items</div>
              <button type="button" className="btn btn-ghost" onClick={addItem}>+ Add Item</button>
            </div>
            <div className="card-body">
              {items.length === 0 ? (
                <div className="empty">
                  <div className="empty-title">No items added</div>
                  <div className="section-sub">Click "+ Add Item" to begin</div>
                </div>
              ) : (
                <div className="auth-form">
                  {items.map((item, index) => (
                    <div className="form-row cols-2" key={`line-${index}`}>
                      <div className="form-group">
                        <label>Product</label>
                        <select value={item.productId} onChange={(event) => updateItem(index, { productId: event.target.value })}>
                          {products.map((product) => (
                            <option key={product.id} value={product.id}>{product.name} ({product.sku})</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Quantity</label>
                        <div style={{ display: "flex", gap: 8 }}>
                          <input type="number" min="1" value={item.quantity} onChange={(event) => updateItem(index, { quantity: event.target.value })} />
                          <button type="button" className="btn btn-ghost" onClick={() => removeItem(index)}>Remove</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-header"><div className="card-title">Summary</div></div>
            <div className="card-body">
              <div className="progress-label"><span>Subtotal</span><span>${computed.subtotal.toFixed(2)}</span></div>
              <div className="progress-label"><span>Tax (15%)</span><span>${computed.tax.toFixed(2)}</span></div>
              <div className="divider" style={{ height: 1, background: "var(--border)", margin: "12px 0" }} />
              <div className="progress-label" style={{ fontSize: 34, fontWeight: 700 }}><span>Total</span><span style={{ color: "var(--accent)" }}>${computed.total.toFixed(2)}</span></div>
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button type="button" className="btn btn-ghost" onClick={() => submitSale({ createInvoice: false })} disabled={saving}>Save Draft</button>
                <button type="button" className="btn btn-primary" onClick={() => submitSale({ createInvoice: true })} disabled={saving}>Save & Create Invoice</button>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header"><div className="card-title">Options</div></div>
            <div className="card-body">
              <label>Payment Method</label>
              <select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)} style={{ marginBottom: 12 }}>
                <option value="cash">Cash</option>
                <option value="card">Card</option>
                <option value="bank">Bank Transfer</option>
              </select>
              <label>Notes</label>
              <textarea rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Internal notes..." />
            </div>
          </div>
        </div>
      </div>

      {saveMessage ? <div className="alert-strip" style={{ marginTop: 16 }}>{saveMessage}</div> : null}

      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-header"><div className="card-title">Recent Sales</div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Customer</th><th>Subtotal</th><th>Tax</th><th>Total</th><th>Date</th><th>Actions</th></tr></thead>
            <tbody>
              {sales.length === 0 ? <EmptyRow cols={7} text="No sales found" /> : sales.map((sale) => (
                <tr key={sale.id}>
                  <td className="td-main">#{sale.id}</td>
                  <td>{sale.customer || "-"}</td>
                  <td>${Number(sale.subtotal).toFixed(2)}</td>
                  <td>${Number(sale.tax).toFixed(2)}</td>
                  <td>${Number(sale.total).toFixed(2)}</td>
                  <td>{new Date(sale.created_at).toLocaleDateString()}</td>
                  <td><button type="button" className="btn btn-ghost" onClick={() => handleDeleteSale(sale.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
