import { Navigate, useLocation } from "react-router-dom"

import { useAuth } from "./AuthContext"

export default function RequireAuth({
  children,
  allowedRoles,
  requireElevated = false,
}) {
  const location = useLocation()
  const { isAuthenticated, role, isElevated } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return <Navigate to="/dashboard" replace />
  }

  if (requireElevated && !isElevated) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
