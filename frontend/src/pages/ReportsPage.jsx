import { useEffect, useState } from "react"
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

export default function ReportsPage() {
  const { selectedBusinessId } = useOutletContext()
  const [report, setReport] = useState(null)
  const [period, setPeriod] = useState("weekly")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    async function loadReport() {
      if (!selectedBusinessId) {
        setReport(null)
        return
      }

      setLoading(true)
      setError("")
      try {
        const params = {
          business: selectedBusinessId,
          period,
        }
        if (startDate) params.start_date = startDate
        if (endDate) params.end_date = endDate

        const { data } = await api.get("reports/", { params })
        setReport(data)
      } catch (err) {
        setError(err?.response?.data?.detail || err.message)
      } finally {
        setLoading(false)
      }
    }

    loadReport()
  }, [selectedBusinessId, period, startDate, endDate])

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Reports</div>
          <div className="section-sub">Daily, weekly, and custom sales/profit reports</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={period} onChange={(event) => setPeriod(event.target.value)}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="all">All Time</option>
          </select>
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
        </div>
      </div>

      {error ? <div className="alert-strip danger">{error}</div> : null}
      {loading ? <div className="section-sub">Loading reports...</div> : null}

      <div className="stats-grid">
        <div className="stat-card green">
          <div className="stat-icon green">$</div>
          <div className="stat-label">Revenue</div>
          <div className="stat-value">${Number(report?.revenue || 0).toFixed(2)}</div>
        </div>
        <div className="stat-card blue">
          <div className="stat-icon blue">EX</div>
          <div className="stat-label">Expenses</div>
          <div className="stat-value">${Number(report?.expenses || 0).toFixed(2)}</div>
        </div>
        <div className="stat-card yellow">
          <div className="stat-icon yellow">PF</div>
          <div className="stat-label">Profit</div>
          <div className="stat-value">${Number(report?.profit || 0).toFixed(2)}</div>
        </div>
        <div className="stat-card red">
          <div className="stat-icon red">SC</div>
          <div className="stat-label">Sales Count</div>
          <div className="stat-value">{report?.sales_count || 0}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Sales Trend ({period})</div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Period</th>
                <th>Total Sales</th>
              </tr>
            </thead>
            <tbody>
              {!report?.sales_trend || report.sales_trend.length === 0 ? (
                <EmptyRow cols={2} text="No trend data for selected filters" />
              ) : (
                report.sales_trend.map((row, index) => (
                  <tr key={`${row.date}-${index}`}>
                    <td className="td-main">{row.date || "-"}</td>
                    <td>${Number(row.total || 0).toFixed(2)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
