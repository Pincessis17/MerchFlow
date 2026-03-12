import { useMemo } from "react"
import { useOutletContext } from "react-router-dom"

function monthKey(dateInput) {
  const date = new Date(dateInput)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
}

export default function ConsoleRevenuePage() {
  const { sales, invoices } = useOutletContext()

  const monthly = useMemo(() => {
    const map = new Map()
    for (const sale of sales) {
      const key = monthKey(sale.created_at)
      map.set(key, (map.get(key) || 0) + Number(sale.total || 0))
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [sales])

  const mrr = useMemo(() => monthly.length ? monthly[monthly.length - 1][1] : 0, [monthly])
  const arr = mrr * 12
  const paid = useMemo(() => invoices.filter((invoice) => invoice.status === "paid").length, [invoices])
  const total = invoices.length || 1
  const paidRate = (paid / total) * 100

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card green"><div className="stat-icon green">$</div><div className="stat-label">MRR</div><div className="stat-value">${mrr.toFixed(2)}</div></div>
        <div className="stat-card blue"><div className="stat-icon blue">AR</div><div className="stat-label">ARR</div><div className="stat-value">${arr.toFixed(2)}</div></div>
        <div className="stat-card yellow"><div className="stat-icon yellow">IV</div><div className="stat-label">Invoices</div><div className="stat-value">{invoices.length}</div></div>
        <div className="stat-card red"><div className="stat-icon red">PR</div><div className="stat-label">Paid Rate</div><div className="stat-value">{paidRate.toFixed(1)}%</div></div>
      </div>

      <div className="card">
        <div className="card-header"><div className="card-title">Monthly Revenue Trend</div></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Month</th><th>Revenue</th></tr></thead>
            <tbody>
              {monthly.map(([month, value]) => (
                <tr key={month}><td className="td-main">{month}</td><td>${value.toFixed(2)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
