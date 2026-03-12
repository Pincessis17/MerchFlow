import { useEffect, useMemo, useState } from "react"
import { useOutletContext } from "react-router-dom"

import api from "../lib/api"

const productTemplate = {
  name: "",
  sku: "",
  cost_price: "",
  selling_price: "",
  stock_quantity: "",
  reorder_level: "",
}

function EmptyProducts({ onAdd }) {
  return (
    <div className="empty" style={{ padding: 56 }}>
      <div style={{ fontSize: 40, marginBottom: 8 }}>??</div>
      <div className="empty-title" style={{ fontSize: 34 }}>No products yet</div>
      <div className="section-sub" style={{ marginBottom: 16 }}>Add your first product to start tracking inventory</div>
      <button type="button" className="btn btn-primary" onClick={onAdd}>+ Add Product</button>
    </div>
  )
}

export default function InventoryPage() {
  const { selectedBusinessId } = useOutletContext()
  const [products, setProducts] = useState([])
  const [productForm, setProductForm] = useState(productTemplate)
  const [editingId, setEditingId] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [search, setSearch] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [savingProduct, setSavingProduct] = useState(false)

  async function loadProducts() {
    if (!selectedBusinessId) {
      setProducts([])
      return
    }

    setLoading(true)
    setError("")
    try {
      const { data } = await api.get("products/", {
        params: { business: selectedBusinessId },
      })
      setProducts(data)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBusinessId])

  const lowStockCount = products.filter((product) => Number(product.stock_quantity) <= Number(product.reorder_level)).length
  const outOfStockCount = products.filter((product) => Number(product.stock_quantity) <= 0).length

  const visibleProducts = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return products
    return products.filter((product) => product.name.toLowerCase().includes(q) || product.sku.toLowerCase().includes(q))
  }, [products, search])

  async function handleCreateOrUpdateProduct(event) {
    event.preventDefault()
    if (!selectedBusinessId) {
      setMessage("Select a business first.")
      return
    }

    setSavingProduct(true)
    setMessage("")
    const payload = {
      business: selectedBusinessId,
      name: productForm.name,
      sku: productForm.sku,
      cost_price: Number(productForm.cost_price || 0),
      selling_price: Number(productForm.selling_price || 0),
      stock_quantity: Number(productForm.stock_quantity || 0),
      reorder_level: Number(productForm.reorder_level || 0),
    }

    try {
      if (editingId) {
        await api.patch(`products/${editingId}/`, payload)
        setMessage("Product updated.")
      } else {
        await api.post("products/", payload)
        setMessage("Product added.")
      }
      setProductForm(productTemplate)
      setEditingId(null)
      setShowForm(false)
      await loadProducts()
    } catch (err) {
      const backendErrors = err?.response?.data
      if (backendErrors && typeof backendErrors === "object") {
        const firstError = Object.values(backendErrors).flat()[0]
        setMessage(String(firstError || "Could not save product."))
      } else {
        setMessage(err?.message || "Could not save product.")
      }
    } finally {
      setSavingProduct(false)
    }
  }

  function handleEdit(product) {
    setEditingId(product.id)
    setShowForm(true)
    setProductForm({
      name: product.name || "",
      sku: product.sku || "",
      cost_price: String(product.cost_price ?? ""),
      selling_price: String(product.selling_price ?? ""),
      stock_quantity: String(product.stock_quantity ?? ""),
      reorder_level: String(product.reorder_level ?? ""),
    })
  }

  async function handleDelete(productId) {
    try {
      await api.delete(`products/${productId}/`)
      setMessage("Product deleted.")
      if (editingId === productId) {
        setEditingId(null)
        setProductForm(productTemplate)
      }
      await loadProducts()
    } catch (err) {
      setMessage(err?.response?.data?.detail || err.message || "Delete failed.")
    }
  }

  return (
    <>
      <div className="section-header" style={{ marginBottom: 12 }}>
        <div>
          <div className="section-title">Inventory</div>
          <div className="section-sub">Manage products and stock</div>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => { setShowForm(true); setEditingId(null); setProductForm(productTemplate) }}>+ Add Product</button>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading inventory...</div> : null}
      {message ? <div className="alert-strip">{message}</div> : null}

      <div className="stats-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
        <div className="stat-card blue"><div className="stat-icon blue">??</div><div className="stat-label">Total Products</div><div className="stat-value">{products.length}</div></div>
        <div className="stat-card yellow"><div className="stat-icon yellow">??</div><div className="stat-label">Low Stock</div><div className="stat-value">{lowStockCount}</div></div>
        <div className="stat-card red"><div className="stat-icon red">?</div><div className="stat-label">Out of Stock</div><div className="stat-value">{outOfStockCount}</div></div>
      </div>

      {showForm ? (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header"><div className="card-title">{editingId ? "Edit Product" : "Add Product"}</div></div>
          <div className="card-body">
            <form onSubmit={handleCreateOrUpdateProduct} className="auth-form">
              <div className="form-row cols-2">
                <div className="form-group"><label>Name</label><input value={productForm.name} onChange={(event) => setProductForm((prev) => ({ ...prev, name: event.target.value }))} required /></div>
                <div className="form-group"><label>SKU</label><input value={productForm.sku} onChange={(event) => setProductForm((prev) => ({ ...prev, sku: event.target.value }))} required /></div>
              </div>
              <div className="form-row cols-2">
                <div className="form-group"><label>Cost Price</label><input type="number" step="0.01" min="0" value={productForm.cost_price} onChange={(event) => setProductForm((prev) => ({ ...prev, cost_price: event.target.value }))} /></div>
                <div className="form-group"><label>Selling Price</label><input type="number" step="0.01" min="0" value={productForm.selling_price} onChange={(event) => setProductForm((prev) => ({ ...prev, selling_price: event.target.value }))} /></div>
              </div>
              <div className="form-row cols-2" style={{ marginBottom: 8 }}>
                <div className="form-group"><label>Stock Quantity</label><input type="number" min="0" value={productForm.stock_quantity} onChange={(event) => setProductForm((prev) => ({ ...prev, stock_quantity: event.target.value }))} /></div>
                <div className="form-group"><label>Reorder Level</label><input type="number" min="0" value={productForm.reorder_level} onChange={(event) => setProductForm((prev) => ({ ...prev, reorder_level: event.target.value }))} /></div>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" className="btn btn-primary" disabled={savingProduct}>{savingProduct ? "Saving..." : editingId ? "Update Product" : "Save Product"}</button>
                <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>Close</button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <div className="card">
        <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="card-title">Products</div>
          <div style={{ display: "flex", gap: 8 }}>
            <input placeholder="Search..." value={search} onChange={(event) => setSearch(event.target.value)} style={{ width: 200 }} />
            <select style={{ width: 160 }}><option>All Categories</option></select>
          </div>
        </div>

        {visibleProducts.length === 0 ? (
          <EmptyProducts onAdd={() => setShowForm(true)} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>SKU</th><th>Name</th><th>Cost</th><th>Selling</th><th>Stock</th><th>Reorder</th><th>Actions</th></tr></thead>
              <tbody>
                {visibleProducts.map((product) => (
                  <tr key={product.id}>
                    <td>{product.sku}</td>
                    <td className="td-main">{product.name}</td>
                    <td>${Number(product.cost_price).toFixed(2)}</td>
                    <td>${Number(product.selling_price).toFixed(2)}</td>
                    <td>{product.stock_quantity}</td>
                    <td>{product.reorder_level}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button type="button" className="btn btn-ghost" onClick={() => handleEdit(product)}>Edit</button>
                        <button type="button" className="btn btn-ghost" onClick={() => handleDelete(product.id)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
