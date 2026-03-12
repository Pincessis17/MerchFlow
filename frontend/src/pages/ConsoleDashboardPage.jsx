import { useMemo } from "react"
import { useNavigate, useOutletContext } from "react-router-dom"

export default function ConsoleDashboardPage() {
  const navigate = useNavigate()
  const { businesses, users, invoices, sales } = useOutletContext()

  const paidInvoices = useMemo(() => invoices.filter((invoice) => invoice.status === "paid").length, [invoices])
  const revenue = useMemo(() => sales.reduce((sum, sale) => sum + Number(sale.total || 0), 0), [sales])

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card green"><div className="stat-icon green">TN</div><div className="stat-label">Total Tenants</div><div className="stat-value">{businesses.length}</div></div>
        <div className="stat-card blue"><div className="stat-icon blue">US</div><div className="stat-label">Total Users</div><div className="stat-value">{users.length}</div></div>
        <div className="stat-card yellow"><div className="stat-icon yellow">$</div><div className="stat-label">Revenue</div><div className="stat-value">${revenue.toFixed(2)}</div></div>
        <div className="stat-card red"><div className="stat-icon red">PD</div><div className="stat-label">Paid Invoices</div><div className="stat-value">{paidInvoices}</div></div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <div className="card-title">Recent Tenants</div>
            <button type="button" className="btn btn-ghost" onClick={() => navigate("/console/tenants")}>View All</button>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Company</th><th>Email</th><th>Created</th></tr></thead>
              <tbody>
                {businesses.slice(0, 8).map((business) => (
                  <tr key={business.id}>
                    <td className="td-main">{business.name}</td>
                    <td>{business.email || "-"}</td>
                    <td>{new Date(business.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Quick Actions</div>
          </div>
          <div className="card-body">
            <div className="quick-actions">
              <button type="button" className="quick-action" onClick={() => navigate("/console/tenants")}>Manage Tenants</button>
              <button type="button" className="quick-action" onClick={() => navigate("/console/plans")}>Manage Plans</button>
              <button type="button" className="quick-action" onClick={() => navigate("/console/revenue")}>Revenue Report</button>
              <button type="button" className="quick-action" onClick={() => navigate("/console/audit")}>Audit Logs</button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
