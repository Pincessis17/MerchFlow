import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"

import { useAuth } from "../auth/AuthContext"

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form, setForm] = useState({ email: "", password: "" })
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    setLoading(true)
    try {
      const user = await login(form.email, form.password)
      navigate("/dashboard", {
        replace: true,
      })
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
            <h1 className="auth-title">MerchFlow Login</h1>
            <p className="auth-sub">Sign in to tenant app or platform console</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
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
          />
          {error ? <div className="alert-strip danger">{error}</div> : null}
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Signing In..." : "Sign In"}
          </button>
        </form>
        <p className="auth-foot">
          New company? <Link to="/register">Create trial account</Link>
        </p>
      </div>
    </div>
  )
}
