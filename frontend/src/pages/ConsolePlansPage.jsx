import { useMemo, useState } from "react"
import { useOutletContext } from "react-router-dom"

const STORAGE_KEY = "console_plans"

function loadPlans() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return [
        { id: "starter", name: "Starter", monthly: 49, yearly: 499, max_users: 10, active: true },
      ]
    }
    return JSON.parse(raw)
  } catch {
    return []
  }
}

function persistPlans(plans) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(plans))
}

export default function ConsolePlansPage() {
  const { users } = useOutletContext()
  const [plans, setPlans] = useState(loadPlans)
  const [message, setMessage] = useState("")
  const [form, setForm] = useState({ id: "", name: "", monthly: "", yearly: "", max_users: "" })

  const ownerCount = useMemo(() => users.filter((user) => user.role === "owner").length, [users])

  function handleCreatePlan(event) {
    event.preventDefault()
    const plan = {
      id: form.id.toLowerCase(),
      name: form.name,
      monthly: Number(form.monthly || 0),
      yearly: Number(form.yearly || 0),
      max_users: Number(form.max_users || 0),
      active: true,
    }
    const next = [...plans.filter((item) => item.id !== plan.id), plan]
    setPlans(next)
    persistPlans(next)
    setMessage("Plan saved.")
    setForm({ id: "", name: "", monthly: "", yearly: "", max_users: "" })
  }

  function handleTogglePlan(planId) {
    const next = plans.map((plan) => (plan.id === planId ? { ...plan, active: !plan.active } : plan))
    setPlans(next)
    persistPlans(next)
    setMessage("Plan updated.")
  }

  return (
    <>
      <div className="section-header">
        <div>
          <div className="section-title">Subscription Plans</div>
          <div className="section-sub">Manage pricing tiers for tenants</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header"><div className="card-title">Create / Update Plan</div></div>
          <div className="card-body">
            <form className="auth-form" onSubmit={handleCreatePlan}>
              <div className="form-row cols-2">
                <div className="form-group"><label>Plan Code</label><input required value={form.id} onChange={(event) => setForm((prev) => ({ ...prev, id: event.target.value }))} /></div>
                <div className="form-group"><label>Plan Name</label><input required value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} /></div>
              </div>
              <div className="form-row cols-2">
                <div className="form-group"><label>Monthly Price</label><input type="number" min="0" value={form.monthly} onChange={(event) => setForm((prev) => ({ ...prev, monthly: event.target.value }))} /></div>
                <div className="form-group"><label>Yearly Price</label><input type="number" min="0" value={form.yearly} onChange={(event) => setForm((prev) => ({ ...prev, yearly: event.target.value }))} /></div>
              </div>
              <div className="form-row" style={{ marginBottom: 8 }}>
                <div className="form-group"><label>Max Users</label><input type="number" min="1" value={form.max_users} onChange={(event) => setForm((prev) => ({ ...prev, max_users: event.target.value }))} /></div>
              </div>
              <button type="submit" className="btn btn-primary">Save Plan</button>
            </form>
            {message ? <div className="alert-strip" style={{ marginTop: 10 }}>{message}</div> : null}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">Plan Stats</div></div>
          <div className="card-body">
            <div className="mini-metric"><div className="mini-metric-val">{plans.length}</div><div className="mini-metric-lbl">Total Plans</div></div>
            <div className="mini-metric"><div className="mini-metric-val">{plans.filter((plan) => plan.active).length}</div><div className="mini-metric-lbl">Active Plans</div></div>
            <div className="mini-metric"><div className="mini-metric-val">{ownerCount}</div><div className="mini-metric-lbl">Tenant Owners</div></div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Code</th><th>Name</th><th>Monthly</th><th>Yearly</th><th>Max Users</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              {plans.map((plan) => (
                <tr key={plan.id}>
                  <td className="td-main">{plan.id}</td>
                  <td>{plan.name}</td>
                  <td>${Number(plan.monthly).toFixed(2)}</td>
                  <td>${Number(plan.yearly).toFixed(2)}</td>
                  <td>{plan.max_users}</td>
                  <td>{plan.active ? "Active" : "Disabled"}</td>
                  <td><button type="button" className="btn btn-ghost" onClick={() => handleTogglePlan(plan.id)}>{plan.active ? "Disable" : "Enable"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
