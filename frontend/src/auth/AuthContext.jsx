import { createContext, useContext, useMemo, useState } from "react"

import api from "../lib/api"

const AuthContext = createContext(null)
const STORAGE_KEY = "business_manager_auth"

function loadAuthState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [authState, setAuthState] = useState(loadAuthState)

  function persist(next) {
    setAuthState(next)
    if (next) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  async function login(email, password) {
    const tokenRes = await api.post("token/", { email, password })
    const usersRes = await api.get("users/")
    const user = usersRes.data.find((u) => u.email.toLowerCase() === email.toLowerCase())
    if (!user) throw new Error("User not found.")
    const state = {
      access: tokenRes.data.access,
      refresh: tokenRes.data.refresh,
      user,
    }
    persist(state)
    return user
  }

  async function register(payload) {
    const businessRes = await api.post("businesses/", {
      name: payload.company_name,
      email: payload.email,
      phone: "",
      address: "",
    })
    await api.post("users/", {
      email: payload.email,
      password: payload.password,
      role: "owner",
      business: businessRes.data.id,
    })
    return login(payload.email, payload.password)
  }

  async function refreshAccess() {
    if (!authState?.refresh) return null
    const refreshRes = await api.post("token/refresh/", {
      refresh: authState.refresh,
    })
    const next = { ...authState, access: refreshRes.data.access }
    persist(next)
    return next
  }

  function logout() {
    persist(null)
  }

  const value = useMemo(
    () => ({
      authState,
      accessToken: authState?.access || null,
      refreshToken: authState?.refresh || null,
      user: authState?.user || null,
      role: authState?.user?.role || null,
      isAuthenticated: Boolean(authState?.access && authState?.user),
      isElevated: true,
      login,
      register,
      refreshAccess,
      elevate: async () => ({ access: authState?.access || "" }),
      logout,
    }),
    [authState],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used inside AuthProvider.")
  return context
}
