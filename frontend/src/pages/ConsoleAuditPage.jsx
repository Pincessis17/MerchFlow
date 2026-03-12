import { useMemo, useState } from "react"
import { useOutletContext } from "react-router-dom"

function buildAuditRows({ businesses, users, sales, invoices }) {
  const rows = []

  for (const business of businesses) {
    rows.push({
      id: `business-${business.id}`,
      time: business.created_at,
      action: "tenant.created",
      actor: business.email || "system",
      target: business.name,
      details: "Business account created",
    })
  }

  for (const user of users) {
    rows.push({
      id: `user-${user.id}`,
      time: user.last_login || user.date_joined || new Date().toISOString(),
      action: "user.record",
      actor: user.email,
      target: `business#${user.business}`,
      details: `Role: ${user.role}`,
    })
  }

  for (const sale of sales) {
    rows.push({
      id: `sale-${sale.id}`,
      time: sale.created_at,
      action: "sale.created",
      actor: "system",
      target: `sale#${sale.id}`,
      details: `Total ${sale.total}`,
    })
  }

  for (const invoice of invoices) {
    rows.push({
      id: `invoice-${invoice.id}`,
      time: invoice.created_at,
      action: "invoice.created",
      actor: "system",
      target: invoice.invoice_number,
      details: `Status: ${invoice.status}`,
    })
  }

  return rows.sort((a, b) => new Date(b.time) - new Date(a.time))
}

function toCsv(rows) {
  const header = "time,action,actor,target,details"
  const body = rows.map((row) => [
    row.time,
    row.action,
    row.actor,
    row.target,
    String(row.details).replaceAll(",", " "),
  ].join(","))
  return [header, ...body].join("\n")
}

export default function ConsoleAuditPage() {
  const { businesses, users, sales, invoices } = useOutletContext()
  const [query, setQuery] = useState("")

  const rows = useMemo(() => buildAuditRows({ businesses, users, sales, invoices }), [businesses, users, sales, invoices])
  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    if (!q) return rows
    return rows.filter((row) =>
      row.action.toLowerCase().includes(q) ||
      row.actor.toLowerCase().includes(q) ||
      row.target.toLowerCase().includes(q),
    )
  }, [rows, query])

  function handleExport() {
    const blob = new Blob([toCsv(filtered)], { type: "text/csv;charset=utf-8;" })
    const link = document.createElement("a")
    link.href = URL.createObjectURL(blob)
    link.download = "audit-logs.csv"
    link.click()
    URL.revokeObjectURL(link.href)
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Audit Logs</div>
          <div className="section-sub">Platform-level activity records</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input placeholder="Filter logs" value={query} onChange={(event) => setQuery(event.target.value)} style={{ width: 220 }} />
          <button type="button" className="btn btn-ghost" onClick={handleExport}>Export CSV</button>
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Target</th><th>Details</th></tr></thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id}>
                  <td>{new Date(row.time).toLocaleString()}</td>
                  <td className="td-main">{row.action}</td>
                  <td>{row.actor}</td>
                  <td>{row.target}</td>
                  <td>{row.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
