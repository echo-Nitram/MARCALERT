import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { isAuthenticated } from './lib/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Alertas from './pages/Alertas'
import Marcas from './pages/Marcas'
import Boletines from './pages/Boletines'
import Billing from './pages/Billing'
import BillingResult from './pages/BillingResult'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function PrivateRoute({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />
}

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <PrivateRoute>
      <Layout>{children}</Layout>
    </PrivateRoute>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/billing/success" element={<BillingResult />} />
          <Route path="/billing/cancel"  element={<BillingResult />} />

          <Route path="/alertas"   element={<AppLayout><Alertas /></AppLayout>} />
          <Route path="/marcas"    element={<AppLayout><Marcas /></AppLayout>} />
          <Route path="/boletines" element={<AppLayout><Boletines /></AppLayout>} />
          <Route path="/billing"   element={<AppLayout><Billing /></AppLayout>} />

          <Route path="/" element={<Navigate to="/alertas" replace />} />
          <Route path="*" element={<Navigate to="/alertas" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
