import { useEffect, useMemo, useState } from "react"
import { useNavigate, useOutletContext } from "react-router-dom"

import api from "../lib/api"

export default function DashboardPage() {
  const navigate = useNavigate()
  const { selectedBusinessId } = useOutletContext()
  const [report, setReport] = useState(null)
  const [sales, setSales] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    async function loadDashboard() {
      if (!selectedBusinessId) {
        setReport(null)
        setSales([])
        setProducts([])
        return
      }

      setLoading(true)
      setError("")
      try {
        const params = { business: selectedBusinessId }
        const [reportRes, salesRes, productsRes] = await Promise.all([
          api.get("reports/", { params: { ...params, period: "weekly" } }),
          api.get("sales/", { params }),
          api.get("products/", { params }),
        ])
        setReport(reportRes.data)
        setSales(salesRes.data)
        setProducts(productsRes.data)
      } catch (err) {
        setError(err?.response?.data?.detail || err.message)
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [selectedBusinessId])

  const todaySales = useMemo(() => {
    const today = new Date().toDateString()
    const todays = sales.filter((sale) => new Date(sale.created_at).toDateString() === today)
    const total = todays.reduce((sum, sale) => sum + Number(sale.total || 0), 0)
    return { count: todays.length, total }
  }, [sales])

  const topProducts = useMemo(() => {
    const productMap = new Map(products.map((product) => [product.id, product]))
    const totals = new Map()
    for (const sale of sales) {
      for (const item of sale.items || []) {
        const qty = Number(item.quantity || 0)
        totals.set(item.product, (totals.get(item.product) || 0) + qty)
      }
    }
    return [...totals.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([productId, qty]) => ({
        id: productId,
        name: productMap.get(productId)?.name || `Product #${productId}`,
        quantity: qty,
      }))
  }, [sales, products])

  const chartData = report?.sales_trend || []
  const maxChart = Math.max(...chartData.map((row) => Number(row.total || 0)), 1)

  return (
    <>
      <div className="section-header" style={{ marginBottom: 12 }}>
        <div>
          <div className="section-title">Dashboard</div>
        </div>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading dashboard...</div> : null}

      <div className="stats-grid">
        <div className="stat-card green">
          <div className="stat-icon green">??</div>
          <div className="stat-label">Total Revenue</div>
          <div className="stat-value">${Number(report?.revenue || 0).toFixed(2)}</div>
          <div className="stat-sub">All time sales</div>
        </div>
        <div className="stat-card blue">
          <div className="stat-icon blue">??</div>
          <div className="stat-label">Today's Sales</div>
          <div className="stat-value">${todaySales.total.toFixed(2)}</div>
          <div className="stat-sub">{todaySales.count} transactions today</div>
        </div>
        <div className="stat-card yellow">
          <div className="stat-icon yellow">??</div>
          <div className="stat-label">Total Products</div>
          <div className="stat-value">{products.length}</div>
          <div className="stat-sub">Active SKUs</div>
        </div>
        <div className="stat-card red">
          <div className="stat-icon red">??</div>
          <div className="stat-label">Low Stock</div>
          <div className="stat-value">{report?.low_stock_count || 0}</div>
          <div className="stat-sub">Need restocking</div>
        </div>
      </div>

      <div className="quick-actions">
        <button type="button" className="quick-action" onClick={() => navigate("/sales")}>? New Sale</button>
        <button type="button" className="quick-action" onClick={() => navigate("/inventory")}>?? Add Product</button>
        <button type="button" className="quick-action" onClick={() => navigate("/expenses")}>?? Record Expense</button>
        <button type="button" className="quick-action" onClick={() => navigate("/inventory")}>?? Receive Stock</button>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><div className="card-title">Sales Trend - Last 7 Days</div></div>
          <div className="card-body">
            {chartData.length === 0 ? (
              <div className="empty"><div className="empty-title">No trend data yet</div></div>
            ) : (
              <>
                <div className="chart-area" style={{ height: 230 }}>
                  {chartData.map((row) => (
                    <div key={row.date} className="chart-bar" style={{ height: `${Math.max((Number(row.total || 0) / maxChart) * 100, 8)}%` }} />
                  ))}
                </div>
                <div className="chart-labels">
                  {chartData.map((row) => (
                    <span key={`lbl-${row.date}`}>{new Date(row.date).toLocaleDateString(undefined, { weekday: "short" })}</span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">Top Selling Products</div></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Product</th><th>Units Sold</th></tr></thead>
              <tbody>
                {topProducts.length === 0 ? (
                  <tr><td colSpan={2}><div className="empty"><div className="empty-title">No sales yet</div><div className="section-sub">Create your first sale to see top products</div></div></td></tr>
                ) : topProducts.map((row) => (
                  <tr key={row.id}><td className="td-main">{row.name}</td><td>{row.quantity}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
