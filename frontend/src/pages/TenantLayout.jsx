import { useEffect, useMemo, useState } from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"

import { useAuth } from "../auth/AuthContext"
import api from "../lib/api"

const navItems = [
  { path: "/dashboard", label: "Dashboard", section: "Overview", icon: "⬡" },
  { path: "/sales", label: "New Sale", section: "Sales", icon: "+" },
  { path: "/invoices", label: "Invoices", section: "Sales", icon: "📄" },
  { path: "/inventory", label: "Inventory", section: "Catalog", icon: "📦" },
  { path: "/customers", label: "Customers", section: "Catalog", icon: "👥" },
  { path: "/settings", label: "Team & Access", section: "Settings", icon: "🔑" },
]

const routeTitles = {
  "/dashboard": "Dashboard",
  "/inventory": "Inventory",
  "/customers": "Customers",
  "/sales": "Create New Sale",
  "/invoices": "Invoices",
  "/expenses": "Expenses",
  "/reports": "Reports",
  "/settings": "Team & Access",
}

function groupNavBySection(items) {
  const grouped = {}
  for (const item of items) {
    if (!grouped[item.section]) grouped[item.section] = []
    grouped[item.section].push(item)
  }
  return grouped
}

const SELECTED_BUSINESS_KEY = "selected_business_id"

export default function TenantLayout() {
  const { user, role, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [businesses, setBusinesses] = useState([])
  const [selectedBusinessId, setSelectedBusinessId] = useState(null)
  const [invoiceCount, setInvoiceCount] = useState(0)
  const [lowStockCount, setLowStockCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const grouped = useMemo(() => groupNavBySection(navItems), [])
  const pageTitle = routeTitles[location.pathname] || "Dashboard"

  useEffect(() => {
    const raw = localStorage.getItem(SELECTED_BUSINESS_KEY)
    if (raw) setSelectedBusinessId(Number(raw))
  }, [])

  useEffect(() => {
    async function loadBusinesses() {
      setLoading(true)
      setError("")
      try {
        const { data } = await api.get("businesses/")
        setBusinesses(data)

        if (data.length === 0) {
          setSelectedBusinessId(null)
          return
        }

        const validSelected = data.find((b) => b.id === selectedBusinessId)
        const nextBusinessId = validSelected ? selectedBusinessId : data[0].id
        setSelectedBusinessId(nextBusinessId)
        localStorage.setItem(SELECTED_BUSINESS_KEY, String(nextBusinessId))
      } catch (err) {
        setError(err?.response?.data?.detail || err.message)
      } finally {
        setLoading(false)
      }
    }

    loadBusinesses()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleBusinessChange(event) {
    const next = Number(event.target.value)
    setSelectedBusinessId(next)
    localStorage.setItem(SELECTED_BUSINESS_KEY, String(next))
  }

  useEffect(() => {
    async function loadSidebarCounts() {
      if (!selectedBusinessId) {
        setInvoiceCount(0)
        setLowStockCount(0)
        return
      }
      try {
        const params = { business: selectedBusinessId }
        const [invoicesRes, productsRes] = await Promise.all([
          api.get("invoices/", { params }),
          api.get("products/", { params }),
        ])
        setInvoiceCount(invoicesRes.data.length)
        const lowCount = productsRes.data.filter((p) => Number(p.stock_quantity) <= Number(p.reorder_level)).length
        setLowStockCount(lowCount)
      } catch {
        setInvoiceCount(0)
        setLowStockCount(0)
      }
    }
    loadSidebarCounts()
  }, [selectedBusinessId])

  function handleLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  const selectedBusiness = businesses.find((b) => b.id === selectedBusinessId)

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">🛒</div>
          <div>
            <div className="logo-text">MerchFlow</div>
            <div className="logo-sub">Business Dashboard</div>
          </div>
        </div>

        <div className="sidebar-section">
          <label>Business</label>
          <select value={selectedBusinessId || ""} onChange={handleBusinessChange}>
            {businesses.map((business) => (
              <option key={business.id} value={business.id}>
                {business.name}
              </option>
            ))}
          </select>
        </div>

        {Object.entries(grouped).map(([section, items]) => (
          <div className="sidebar-section" key={section}>
            <div className="sidebar-section-label">{section}</div>
            {items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
                {item.path === "/invoices" && invoiceCount > 0 ? <span className="nav-badge">{invoiceCount}</span> : null}
                {item.path === "/inventory" && lowStockCount > 0 ? <span className="nav-badge warning">{lowStockCount}</span> : null}
              </NavLink>
            ))}
          </div>
        ))}

        <div className="sidebar-footer">
          {role === "owner" ? <Link className="console-switch" to="/console/dashboard">Platform Console</Link> : null}
          <div className="user-card" style={{ marginTop: 8 }}>
            <div className="user-avatar">PO</div>
            <div>
              <div className="user-name">Platform Owner</div>
              <div className="user-role">Admin · {user?.email || "owner@merchflow"}</div>
            </div>
          </div>
          <button type="button" className="btn btn-ghost" style={{ width: "100%", marginTop: 8 }} onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="topbar-left">
            <div>
              <div className="topbar-title">{pageTitle}</div>
            </div>
          </div>
          <div className="topbar-right">
            <button type="button" className="icon-btn" aria-label="Notifications">🔔</button>
            <button type="button" className="icon-btn" aria-label="Settings">⚙️</button>
            <button type="button" className="btn btn-primary" onClick={() => navigate("/sales")}>+ New Sale</button>
            {loading ? <span className="section-sub">Loading...</span> : null}
            {!selectedBusinessId && !loading ? <span className="section-sub">No business selected</span> : null}
            {error ? <span className="section-sub">{error}</span> : null}
          </div>
        </div>

        <div className="content">
          <Outlet
            context={{
              selectedBusinessId,
              selectedBusiness,
              businesses,
            }}
          />
        </div>
      </main>
    </div>
  )
}
