import { useEffect, useMemo, useState } from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"

import { useAuth } from "../auth/AuthContext"
import api from "../lib/api"

const navItems = [
  { path: "/console/dashboard", label: "Overview", section: "Platform", icon: "OV" },
  { path: "/console/tenants", label: "Tenants", section: "Platform", icon: "TN" },
  { path: "/console/plans", label: "Plans", section: "Billing", icon: "PL" },
  { path: "/console/revenue", label: "Revenue", section: "Billing", icon: "RV" },
  { path: "/console/audit", label: "Audit Logs", section: "Security", icon: "AL" },
]

const routeTitles = {
  "/console/dashboard": "Platform Overview",
  "/console/tenants": "Tenants",
  "/console/plans": "Subscription Plans",
  "/console/revenue": "Revenue",
  "/console/audit": "Audit Logs",
}

function groupBySection(items) {
  const grouped = {}
  for (const item of items) {
    if (!grouped[item.section]) grouped[item.section] = []
    grouped[item.section].push(item)
  }
  return grouped
}

export default function ConsoleLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [businesses, setBusinesses] = useState([])
  const [users, setUsers] = useState([])
  const [sales, setSales] = useState([])
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const grouped = useMemo(() => groupBySection(navItems), [])
  const pageTitle = routeTitles[location.pathname] || "Platform Overview"

  async function loadConsoleData() {
    setLoading(true)
    setError("")
    try {
      const [businessRes, usersRes, salesRes, invoicesRes] = await Promise.all([
        api.get("businesses/"),
        api.get("users/"),
        api.get("sales/"),
        api.get("invoices/"),
      ])
      setBusinesses(businessRes.data)
      setUsers(usersRes.data)
      setSales(salesRes.data)
      setInvoices(invoicesRes.data)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConsoleData()
  }, [])

  function handleLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">MF</div>
          <div>
            <div className="logo-text">MerchFlow</div>
            <div className="logo-sub">Platform Console</div>
          </div>
        </div>

        {Object.entries(grouped).map(([section, items]) => (
          <div className="sidebar-section" key={section}>
            <div className="sidebar-section-label">{section}</div>
            {items.map((item) => (
              <NavLink key={item.path} to={item.path} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}

        <div className="sidebar-footer">
          <Link className="console-switch" to="/dashboard">Tenant App</Link>
          <div className="user-card" style={{ marginTop: 8 }}>
            <div className="user-avatar">{(user?.email || "U").slice(0, 2).toUpperCase()}</div>
            <div>
              <div className="user-name">Platform Owner</div>
              <div className="user-role">{user?.email || "owner@local"}</div>
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
              <div className="topbar-breadcrumb">Platform / {pageTitle}</div>
            </div>
          </div>
          <div className="topbar-right">
            {loading ? <span className="section-sub">Loading...</span> : null}
            {error ? <span className="section-sub">{error}</span> : null}
          </div>
        </div>
        <div className="content">
          <Outlet context={{ businesses, users, sales, invoices, reload: loadConsoleData }} />
        </div>
      </main>
    </div>
  )
}
