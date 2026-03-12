import { Navigate, Route, Routes } from "react-router-dom"

import { useAuth } from "./auth/AuthContext"
import RequireAuth from "./auth/RequireAuth"
import CustomersPage from "./pages/CustomersPage"
import ConsoleAuditPage from "./pages/ConsoleAuditPage"
import ConsoleDashboardPage from "./pages/ConsoleDashboardPage"
import ConsoleLayout from "./pages/ConsoleLayout"
import ConsolePlansPage from "./pages/ConsolePlansPage"
import ConsoleRevenuePage from "./pages/ConsoleRevenuePage"
import ConsoleTenantsPage from "./pages/ConsoleTenantsPage"
import DashboardPage from "./pages/DashboardPage"
import ExpensesPage from "./pages/ExpensesPage"
import InventoryPage from "./pages/InventoryPage"
import InvoicesPage from "./pages/InvoicesPage"
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage"
import ReportsPage from "./pages/ReportsPage"
import SalesPage from "./pages/SalesPage"
import SettingsPage from "./pages/SettingsPage"
import TenantLayout from "./pages/TenantLayout"

function HomeRedirect() {
  const { isAuthenticated, role } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (role === "owner") return <Navigate to="/console/dashboard" replace />
  return <Navigate to="/dashboard" replace />
}

function ProtectedTenantRoutes() {
  return (
    <RequireAuth allowedRoles={["owner", "manager", "staff"]}>
      <TenantLayout />
    </RequireAuth>
  )
}

function ProtectedConsoleRoutes() {
  return (
    <RequireAuth allowedRoles={["owner"]}>
      <ConsoleLayout />
    </RequireAuth>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedTenantRoutes />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/sales" element={<SalesPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
        <Route path="/expenses" element={<ExpensesPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route element={<ProtectedConsoleRoutes />}>
        <Route path="/console/dashboard" element={<ConsoleDashboardPage />} />
        <Route path="/console/tenants" element={<ConsoleTenantsPage />} />
        <Route path="/console/plans" element={<ConsolePlansPage />} />
        <Route path="/console/revenue" element={<ConsoleRevenuePage />} />
        <Route path="/console/audit" element={<ConsoleAuditPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
