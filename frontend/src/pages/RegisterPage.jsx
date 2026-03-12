import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { useAuth } from "../auth/AuthContext"

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const [form, setForm] = useState({
    company_name: "",
    subdomain: "",
    name: "",
    email: "",
    password: "",
  })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    setLoading(true)
    try {
      await register(form)
      navigate("/dashboard", { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-title-wrap">
          <div className="logo-icon">MF</div>
          <div>
            <h1 className="auth-title">Create Tenant Account</h1>
            <p className="auth-sub">Start a trial company workspace</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          <label>Company Name</label>
          <input
            value={form.company_name}
            onChange={(event) => setForm((prev) => ({ ...prev, company_name: event.target.value }))}
            required
          />
          <label>Subdomain</label>
          <input
            value={form.subdomain}
            onChange={(event) => setForm((prev) => ({ ...prev, subdomain: event.target.value }))}
            required
          />
          <label>Your Name</label>
          <input
            value={form.name}
            onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            required
          />
          <label>Email</label>
          <input
            type="email"
            value={form.email}
            onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            required
          />
          <label>Password</label>
          <input
            type="password"
            value={form.password}
            onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
            required
            minLength={8}
          />
          {error ? <div className="alert-strip danger">{error}</div> : null}
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Creating..." : "Create Account"}
          </button>
        </form>
        <p className="auth-foot">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
