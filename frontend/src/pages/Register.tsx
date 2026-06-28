import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../lib/api'
import { setToken } from '../lib/auth'

export default function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', tenant_name: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(field: string) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authApi.register(form)
      setToken(res.data.access_token)
      navigate('/alertas')
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Error al registrar')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-600 px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">MARCALERT</h1>
          <p className="mt-2 text-brand-100">30 días de prueba gratis, sin tarjeta</p>
        </div>
        <div className="card p-8">
          <h2 className="mb-6 text-xl font-semibold text-gray-900">Crear cuenta</h2>
          {error && (
            <div className="mb-4 rounded-md bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Nombre del estudio o agencia
              </label>
              <input
                className="input"
                placeholder="Ej: Estudio García & Asociados"
                value={form.tenant_name}
                onChange={set('tenant_name')}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Tu nombre</label>
              <input
                className="input"
                placeholder="Nombre completo"
                value={form.full_name}
                onChange={set('full_name')}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                className="input"
                value={form.email}
                onChange={set('email')}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Contraseña</label>
              <input
                type="password"
                className="input"
                value={form.password}
                onChange={set('password')}
                required
                minLength={8}
              />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? 'Creando cuenta...' : 'Comenzar prueba gratuita'}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-gray-500">
            ¿Ya tenés cuenta?{' '}
            <Link to="/login" className="font-medium text-brand-600 hover:underline">
              Ingresar
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
