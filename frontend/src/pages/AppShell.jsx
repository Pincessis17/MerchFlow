import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { useAuth } from "../auth/AuthContext"
import api from "../lib/api"

const tenantNav = [
  { id: "dashboard", label: "Dashboard", section: "Overview", icon: "DG" },
  { id: "new-sale", label: "Sales / POS", section: "Sales", icon: "SL" },
  { id: "invoices", label: "Invoices", section: "Sales", icon: "IV" },
  { id: "inventory", label: "Inventory", section: "Catalog", icon: "IN" },
  { id: "customers", label: "Customers", section: "Catalog", icon: "CU" },
  { id: "expenses", label: "Expenses", section: "Finance", icon: "EX" },
  { id: "reports", label: "Reports", section: "Finance", icon: "RP" },
  { id: "settings", label: "Settings", section: "Settings", icon: "ST" },
]

const consoleNav = [
  { id: "console-dashboard", label: "Overview", section: "Platform", icon: "OV" },
  { id: "console-tenants", label: "Tenants", section: "Platform", icon: "TN" },
  { id: "console-reports", label: "Reports", section: "Platform", icon: "RP" },
]

const pageTitles = {
  dashboard: "Dashboard",
  "new-sale": "Sales / POS",
  invoices: "Invoices",
  inventory: "Inventory",
  customers: "Customers",
  expenses: "Expenses",
  reports: "Reports",
  settings: "Settings",
  "console-dashboard": "Platform Overview",
  "console-tenants": "Tenants",
  "console-reports": "Platform Reports",
}

const productTemplate = {
  name: "",
  sku: "",
  cost_price: "",
  selling_price: "",
  stock_quantity: "",
  reorder_level: "",
}

function groupNavBySection(items) {
  const grouped = {}
  for (const item of items) {
    if (!grouped[item.section]) grouped[item.section] = []
    grouped[item.section].push(item)
  }
  return grouped
}

function badgeClass(status) {
  if (status === "paid" || status === "active") return "badge badge-green"
  if (status === "pending" || status === "trial") return "badge badge-yellow"
  if (status === "cancelled") return "badge badge-red"
  return "badge badge-gray"
}

function SectionHeader({ title, sub, actionLabel, onAction }) {
  return (
    <div className="section-header">
      <div>
        <div className="section-title">{title}</div>
        <div className="section-sub">{sub}</div>
      </div>
      {actionLabel ? (
        <button type="button" className="btn btn-primary" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
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

function parseCsvRows(csvText) {
  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  if (lines.length === 0) return []

  const header = lines[0].toLowerCase()
  const hasHeader = header.includes("name") && header.includes("sku")
  const dataLines = hasHeader ? lines.slice(1) : lines

  return dataLines.map((line) => {
    const [name, sku, costPrice, sellingPrice, stockQuantity, reorderLevel] = line.split(",").map((part) => part.trim())
    return {
      name: name || "",
      sku: sku || "",
      cost_price: Number(costPrice || 0),
      selling_price: Number(sellingPrice || 0),
      stock_quantity: Number(stockQuantity || 0),
      reorder_level: Number(reorderLevel || 0),
    }
  })
}

export default function AppShell({ mode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [active, setActive] = useState(mode === "console" ? "console-dashboard" : "dashboard")

  const [businesses, setBusinesses] = useState([])
  const [selectedBusinessId, setSelectedBusinessId] = useState(null)
  const [products, setProducts] = useState([])
  const [customers, setCustomers] = useState([])
  const [sales, setSales] = useState([])
  const [invoices, setInvoices] = useState([])
  const [expenses, setExpenses] = useState([])
  const [report, setReport] = useState(null)

  const [productForm, setProductForm] = useState(productTemplate)
  const [csvText, setCsvText] = useState("")
  const [inventoryMessage, setInventoryMessage] = useState("")

  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [savingProduct, setSavingProduct] = useState(false)
  const [importingProducts, setImportingProducts] = useState(false)

  const navItems = mode === "console" ? consoleNav : tenantNav
  const grouped = useMemo(() => groupNavBySection(navItems), [navItems])
  const pageTitle = pageTitles[active] || "Dashboard"

  async function loadBusinesses() {
    const { data } = await api.get("businesses/")
    setBusinesses(data)
    if (!selectedBusinessId && data.length > 0) {
      setSelectedBusinessId(data[0].id)
    }
  }

  async function loadTenantData(businessId) {
    if (!businessId) {
      setProducts([])
      setCustomers([])
      setSales([])
      setInvoices([])
      setExpenses([])
      setReport(null)
      return
    }

    const params = { business: businessId }
    const [productsRes, customersRes, salesRes, invoicesRes, expensesRes, reportsRes] = await Promise.all([
      api.get("products/", { params }),
      api.get("customers/", { params }),
      api.get("sales/", { params }),
      api.get("invoices/", { params }),
      api.get("expenses/", { params }),
      api.get("reports/", { params }),
    ])

    setProducts(productsRes.data)
    setCustomers(customersRes.data)
    setSales(salesRes.data)
    setInvoices(invoicesRes.data)
    setExpenses(expensesRes.data)
    setReport(reportsRes.data)
  }

  async function bootstrap() {
    setLoading(true)
    setError("")
    try {
      await loadBusinesses()
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    bootstrap()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    loadTenantData(selectedBusinessId).catch((err) => {
      setError(err?.response?.data?.detail || err.message)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBusinessId])

  async function refreshTenantData() {
    setError("")
    try {
      await loadTenantData(selectedBusinessId)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    }
  }

  async function handleCreateSampleSale() {
    if (!selectedBusinessId || products.length === 0) return
    const product = products[0]
    const customer = customers[0] || null
    const quantity = 1
    const unitPrice = Number(product.selling_price || 0)
    const lineTotal = unitPrice * quantity

    await api.post("sales/", {
      business: selectedBusinessId,
      customer: customer ? customer.id : null,
      items: [
        {
          product: product.id,
          quantity,
          unit_price: unitPrice,
          line_total: lineTotal,
        },
      ],
    })
    await loadTenantData(selectedBusinessId)
    setActive("reports")
  }

  async function handleCreateProduct(event) {
    event.preventDefault()
    if (!selectedBusinessId) {
      setInventoryMessage("Select a business first.")
      return
    }

    setSavingProduct(true)
    setInventoryMessage("")
    try {
      await api.post("products/", {
        business: selectedBusinessId,
        name: productForm.name,
        sku: productForm.sku,
        cost_price: Number(productForm.cost_price || 0),
        selling_price: Number(productForm.selling_price || 0),
        stock_quantity: Number(productForm.stock_quantity || 0),
        reorder_level: Number(productForm.reorder_level || 0),
      })
      setProductForm(productTemplate)
      setInventoryMessage("Product added.")
      await loadTenantData(selectedBusinessId)
    } catch (err) {
      const backendErrors = err?.response?.data
      if (backendErrors && typeof backendErrors === "object") {
        const firstError = Object.values(backendErrors).flat()[0]
        setInventoryMessage(String(firstError || "Could not add product."))
      } else {
        setInventoryMessage(err?.message || "Could not add product.")
      }
    } finally {
      setSavingProduct(false)
    }
  }

  async function handleImportProducts(event) {
    event.preventDefault()
    if (!selectedBusinessId) {
      setInventoryMessage("Select a business first.")
      return
    }

    const rows = parseCsvRows(csvText)
    if (rows.length === 0) {
      setInventoryMessage("Paste at least one CSV row.")
      return
    }

    const invalidRow = rows.find((row) => !row.name || !row.sku)
    if (invalidRow) {
      setInventoryMessage("Every row must include name and sku.")
      return
    }

    setImportingProducts(true)
    setInventoryMessage("")
    try {
      for (const row of rows) {
        await api.post("products/", {
          business: selectedBusinessId,
          ...row,
        })
      }
      setCsvText("")
      setInventoryMessage(`Imported ${rows.length} product(s).`)
      await loadTenantData(selectedBusinessId)
    } catch (err) {
      setInventoryMessage(err?.response?.data?.detail || err.message || "CSV import failed.")
    } finally {
      setImportingProducts(false)
    }
  }

  function handleLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  const unpaidCount = invoices.filter((i) => i.status !== "paid").length
  const lowStockCount = products.filter((p) => Number(p.stock_quantity) <= Number(p.reorder_level)).length
  const selectedBusiness = businesses.find((b) => b.id === selectedBusinessId)

  function renderTenantContent() {
    if (active === "new-sale") {
      return (
        <>
          <SectionHeader title="Sales / POS" sub="Create and record live sales from inventory" actionLabel="Create Sample Sale" onAction={handleCreateSampleSale} />
          <div className="card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>ID</th><th>Customer</th><th>Subtotal</th><th>Tax</th><th>Total</th><th>Date</th></tr></thead>
                <tbody>
                  {sales.length === 0 ? <EmptyRow cols={6} text="No sales yet" /> : sales.map((s) => (
                    <tr key={s.id}>
                      <td className="td-main">#{s.id}</td>
                      <td>{s.customer || "-"}</td>
                      <td>${Number(s.subtotal).toFixed(2)}</td>
                      <td>${Number(s.tax).toFixed(2)}</td>
                      <td>${Number(s.total).toFixed(2)}</td>
                      <td>{new Date(s.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )
    }

    if (active === "inventory") {
      return (
        <>
          <SectionHeader title="Inventory" sub="Live product catalog from database" actionLabel="Refresh" onAction={refreshTenantData} />

          <div className="grid-2" style={{ marginBottom: 20 }}>
            <div className="card">
              <div className="card-header"><div className="card-title">Add Product</div></div>
              <div className="card-body">
                <form onSubmit={handleCreateProduct} className="auth-form">
                  <div className="form-row cols-2">
                    <div className="form-group">
                      <label>Name</label>
                      <input value={productForm.name} onChange={(event) => setProductForm((prev) => ({ ...prev, name: event.target.value }))} required />
                    </div>
                    <div className="form-group">
                      <label>SKU</label>
                      <input value={productForm.sku} onChange={(event) => setProductForm((prev) => ({ ...prev, sku: event.target.value }))} required />
                    </div>
                  </div>

                  <div className="form-row cols-2">
                    <div className="form-group">
                      <label>Cost Price</label>
                      <input type="number" step="0.01" min="0" value={productForm.cost_price} onChange={(event) => setProductForm((prev) => ({ ...prev, cost_price: event.target.value }))} />
                    </div>
                    <div className="form-group">
                      <label>Selling Price</label>
                      <input type="number" step="0.01" min="0" value={productForm.selling_price} onChange={(event) => setProductForm((prev) => ({ ...prev, selling_price: event.target.value }))} />
                    </div>
                  </div>

                  <div className="form-row cols-2" style={{ marginBottom: 10 }}>
                    <div className="form-group">
                      <label>Stock Quantity</label>
                      <input type="number" min="0" value={productForm.stock_quantity} onChange={(event) => setProductForm((prev) => ({ ...prev, stock_quantity: event.target.value }))} />
                    </div>
                    <div className="form-group">
                      <label>Reorder Level</label>
                      <input type="number" min="0" value={productForm.reorder_level} onChange={(event) => setProductForm((prev) => ({ ...prev, reorder_level: event.target.value }))} />
                    </div>
                  </div>

                  <button type="submit" className="btn btn-primary" disabled={savingProduct}>
                    {savingProduct ? "Saving..." : "Save Product"}
                  </button>
                </form>
              </div>
            </div>

            <div className="card">
              <div className="card-header"><div className="card-title">Bulk Import (CSV)</div></div>
              <div className="card-body">
                <form onSubmit={handleImportProducts} className="auth-form">
                  <label>Paste CSV rows</label>
                  <textarea
                    rows={10}
                    value={csvText}
                    onChange={(event) => setCsvText(event.target.value)}
                    placeholder="name,sku,cost_price,selling_price,stock_quantity,reorder_level&#10;Paracetamol 500mg,P-1001,1.20,2.50,30,10"
                    style={{ resize: "vertical" }}
                  />
                  <button type="submit" className="btn btn-ghost" disabled={importingProducts}>
                    {importingProducts ? "Importing..." : "Import Products"}
                  </button>
                </form>
                <p className="section-sub" style={{ marginTop: 10 }}>
                  Expected columns: name, sku, cost_price, selling_price, stock_quantity, reorder_level.
                </p>
              </div>
            </div>
          </div>

          {inventoryMessage ? <div className="alert-strip">{inventoryMessage}</div> : null}

          <div className="card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>SKU</th><th>Name</th><th>Cost</th><th>Selling</th><th>Stock</th><th>Reorder</th></tr></thead>
                <tbody>
                  {products.length === 0 ? <EmptyRow cols={6} text="No products found" /> : products.map((p) => (
                    <tr key={p.id}>
                      <td>{p.sku}</td>
                      <td className="td-main">{p.name}</td>
                      <td>${Number(p.cost_price).toFixed(2)}</td>
                      <td>${Number(p.selling_price).toFixed(2)}</td>
                      <td>{p.stock_quantity}</td>
                      <td>{p.reorder_level}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )
    }

    if (active === "customers") {
      return (
        <>
          <SectionHeader title="Customers" sub="Customer data from API" />
          <div className="card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Name</th><th>Email</th><th>Phone</th></tr></thead>
                <tbody>
                  {customers.length === 0 ? <EmptyRow cols={3} text="No customers found" /> : customers.map((c) => (
                    <tr key={c.id}><td className="td-main">{c.name}</td><td>{c.email || "-"}</td><td>{c.phone || "-"}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )
    }

    if (active === "invoices") {
      return (
        <>
          <SectionHeader title="Invoices" sub="Live invoice status and payments" />
          <div className="card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Invoice</th><th>Sale</th><th>Status</th><th>Paid</th><th>Total</th><th>Date</th></tr></thead>
                <tbody>
                  {invoices.length === 0 ? <EmptyRow cols={6} text="No invoices found" /> : invoices.map((inv) => (
                    <tr key={inv.id}>
                      <td className="td-main">{inv.invoice_number}</td>
                      <td>#{inv.sale}</td>
                      <td><span className={badgeClass(inv.status)}>{inv.status}</span></td>
                      <td>${Number(inv.amount_paid).toFixed(2)}</td>
                      <td>${Number(inv.total || 0).toFixed(2)}</td>
                      <td>{new Date(inv.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )
    }

    if (active === "expenses") {
      return (
        <>
          <SectionHeader title="Expenses" sub="Business expenses tracked from API" />
          <div className="card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Category</th><th>Description</th><th>Amount</th><th>Date</th></tr></thead>
                <tbody>
                  {expenses.length === 0 ? <EmptyRow cols={4} text="No expenses found" /> : expenses.map((exp) => (
                    <tr key={exp.id}>
                      <td className="td-main">{exp.category}</td>
                      <td>{exp.description || "-"}</td>
                      <td>${Number(exp.amount).toFixed(2)}</td>
                      <td>{new Date(exp.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )
    }

    if (active === "reports") {
      return (
        <>
          <SectionHeader title="Reports" sub="Live operational metrics from the reports endpoint" />
          <div className="stats-grid">
            <div className="stat-card green"><div className="stat-icon green">$</div><div className="stat-label">Revenue</div><div className="stat-value">${Number(report?.revenue || 0).toFixed(2)}</div></div>
            <div className="stat-card blue"><div className="stat-icon blue">EX</div><div className="stat-label">Expenses</div><div className="stat-value">${Number(report?.expenses || 0).toFixed(2)}</div></div>
            <div className="stat-card yellow"><div className="stat-icon yellow">PF</div><div className="stat-label">Profit</div><div className="stat-value">${Number(report?.profit || 0).toFixed(2)}</div></div>
            <div className="stat-card red"><div className="stat-icon red">LS</div><div className="stat-label">Low Stock</div><div className="stat-value">{report?.low_stock_count || 0}</div></div>
          </div>
        </>
      )
    }

    if (active === "dashboard") {
      return (
        <>
          <SectionHeader title="Dashboard" sub="Live metrics and operational shortcuts" />

          <div className="stats-grid">
            <div className="stat-card green"><div className="stat-icon green">$</div><div className="stat-label">Revenue</div><div className="stat-value">${Number(report?.revenue || 0).toFixed(2)}</div></div>
            <div className="stat-card blue"><div className="stat-icon blue">IV</div><div className="stat-label">Unpaid Invoices</div><div className="stat-value">{unpaidCount}</div></div>
            <div className="stat-card yellow"><div className="stat-icon yellow">PR</div><div className="stat-label">Products</div><div className="stat-value">{products.length}</div></div>
            <div className="stat-card red"><div className="stat-icon red">LS</div><div className="stat-label">Low Stock</div><div className="stat-value">{lowStockCount}</div></div>
          </div>

          <div className="quick-actions">
            <button type="button" className="quick-action" onClick={() => setActive("new-sale")}>New Sale</button>
            <button type="button" className="quick-action" onClick={() => setActive("inventory")}>Add Inventory</button>
            <button type="button" className="quick-action" onClick={() => setActive("customers")}>Manage Customers</button>
            <button type="button" className="quick-action" onClick={() => setActive("reports")}>Open Reports</button>
          </div>

          <div className="grid-2">
            <div className="card">
              <div className="card-header"><div className="card-title">Recent Sales</div></div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>ID</th><th>Total</th><th>Date</th></tr></thead>
                  <tbody>
                    {sales.length === 0 ? <EmptyRow cols={3} text="No sales yet" /> : sales.slice(0, 8).map((s) => (
                      <tr key={s.id}><td className="td-main">#{s.id}</td><td>${Number(s.total).toFixed(2)}</td><td>{new Date(s.created_at).toLocaleDateString()}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-header"><div className="card-title">Low Stock Watch</div></div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>SKU</th><th>Name</th><th>Stock</th><th>Reorder</th></tr></thead>
                  <tbody>
                    {products.filter((p) => Number(p.stock_quantity) <= Number(p.reorder_level)).length === 0 ? (
                      <EmptyRow cols={4} text="No low stock products" />
                    ) : (
                      products
                        .filter((p) => Number(p.stock_quantity) <= Number(p.reorder_level))
                        .slice(0, 8)
                        .map((p) => (
                          <tr key={p.id}><td>{p.sku}</td><td className="td-main">{p.name}</td><td>{p.stock_quantity}</td><td>{p.reorder_level}</td></tr>
                        ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )
    }

    return (
      <>
        <SectionHeader title="Settings" sub="Current selected business context" />
        <div className="card">
          <div className="card-body">
            <p className="section-sub">Business: {selectedBusiness?.name || "Not selected"}</p>
            <p className="section-sub">User: {user?.email || "Anonymous"}</p>
          </div>
        </div>
      </>
    )
  }

  function renderConsoleContent() {
    if (active === "console-tenants") {
      return (
        <>
          <SectionHeader title="Tenants" sub="All businesses in the database" />
          <div className="card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Address</th><th>Created</th></tr></thead>
                <tbody>
                  {businesses.length === 0 ? <EmptyRow cols={5} text="No businesses found" /> : businesses.map((b) => (
                    <tr key={b.id}><td className="td-main">{b.name}</td><td>{b.email || "-"}</td><td>{b.phone || "-"}</td><td>{b.address || "-"}</td><td>{new Date(b.created_at).toLocaleDateString()}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )
    }

    return (
      <>
        <SectionHeader title={active === "console-reports" ? "Platform Reports" : "Platform Overview"} sub="Cross-tenant live statistics" />
        <div className="stats-grid">
          <div className="stat-card green"><div className="stat-icon green">TN</div><div className="stat-label">Businesses</div><div className="stat-value">{businesses.length}</div></div>
          <div className="stat-card blue"><div className="stat-icon blue">PR</div><div className="stat-label">Products</div><div className="stat-value">{products.length}</div></div>
          <div className="stat-card yellow"><div className="stat-icon yellow">CU</div><div className="stat-label">Customers</div><div className="stat-value">{customers.length}</div></div>
          <div className="stat-card red"><div className="stat-icon red">IV</div><div className="stat-label">Invoices</div><div className="stat-value">{invoices.length}</div></div>
        </div>
      </>
    )
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">MF</div>
          <div>
            <div className="logo-text">Business Manager</div>
            <div className="logo-sub">{mode === "console" ? "Platform Console" : selectedBusiness?.name || "Tenant App"}</div>
          </div>
        </div>
        {mode === "tenant" ? (
          <div className="sidebar-section">
            <label>Business</label>
            <select value={selectedBusinessId || ""} onChange={(e) => setSelectedBusinessId(Number(e.target.value))}>
              {businesses.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>
        ) : null}

        {Object.entries(grouped).map(([section, items]) => (
          <div className="sidebar-section" key={section}>
            <div className="sidebar-section-label">{section}</div>
            {items.map((item) => {
              let badge = null
              let badgeType = ""
              if (item.id === "invoices") badge = unpaidCount
              if (item.id === "inventory") {
                badge = lowStockCount
                badgeType = "warning"
              }
              if (item.id === "console-tenants") badge = businesses.length
              return (
                <button key={item.id} type="button" className={`nav-item ${active === item.id ? "active" : ""}`} onClick={() => setActive(item.id)}>
                  <span className="nav-icon">{item.icon}</span>
                  {item.label}
                  {badge ? <span className={`nav-badge ${badgeType}`}>{badge}</span> : null}
                </button>
              )
            })}
          </div>
        ))}

        <div className="sidebar-footer">
          {mode === "console" ? <Link className="console-switch" to="/app">Tenant App</Link> : <Link className="console-switch" to="/console">Platform Console</Link>}
          <div className="user-card" style={{ marginTop: 8 }}>
            <div className="user-avatar">{(user?.email || "U").slice(0, 2).toUpperCase()}</div>
            <div>
              <div className="user-name">{user?.name || "Demo User"}</div>
              <div className="user-role">{user?.email || "local@demo"}</div>
            </div>
          </div>
          <button type="button" className="btn btn-ghost" style={{ width: "100%", marginTop: 8 }} onClick={handleLogout}>Sign Out</button>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="topbar-left">
            <div>
              <div className="topbar-title">{pageTitle}</div>
              <div className="topbar-breadcrumb">{mode === "console" ? `Platform / ${pageTitle}` : `Tenant / ${pageTitle}`}</div>
            </div>
          </div>
          <div className="topbar-right">
            {loading ? <span className="section-sub">Loading...</span> : null}
            {!selectedBusinessId && mode === "tenant" && !loading ? <span className="section-sub">No business selected</span> : null}
            {error ? <span className="section-sub">{error}</span> : null}
          </div>
        </div>
        <div className="content">{mode === "console" ? renderConsoleContent() : renderTenantContent()}</div>
      </main>
    </div>
  )
}
