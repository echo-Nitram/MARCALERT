import { Link, NavLink, useNavigate } from 'react-router-dom'
import { clearToken } from '../lib/auth'

const navItems = [
  { to: '/alertas',  label: 'Alertas',   icon: '🔔' },
  { to: '/marcas',   label: 'Cartera',    icon: '🏷️' },
  { to: '/boletines',label: 'Boletines',  icon: '📄' },
  { to: '/billing',  label: 'Suscripción',icon: '💳' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()

  function handleLogout() {
    clearToken()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col bg-brand-600 text-white shadow-lg">
        <div className="flex h-16 items-center px-6">
          <span className="text-xl font-bold tracking-tight">MARCALERT</span>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'text-white/80 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <span>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/20 p-4">
          <button
            onClick={handleLogout}
            className="w-full rounded-md px-3 py-2 text-left text-sm text-white/70 hover:bg-white/10 hover:text-white transition-colors"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
