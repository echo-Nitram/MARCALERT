import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '/api' })

// Inyectar token JWT en cada request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirigir a login en 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string; tenant_name: string }) =>
    api.post<{ access_token: string }>('/auth/register', data),
  login: (email: string, password: string) =>
    api.post<{ access_token: string }>(
      '/auth/token',
      new URLSearchParams({ username: email, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),
  me: () => api.get<{ id: string; email: string; full_name: string; tenant_id: string }>('/auth/me'),
}

// ── Marcas ────────────────────────────────────────────────────────────────────
export type TipoMarca = 'denominativa' | 'figurativa' | 'mixta'
export type Sensibilidad = 'bajo' | 'medio' | 'alto'

export interface Marca {
  id: string
  denominacion: string
  tipo: TipoMarca
  clases_niza: number[]
  sensibilidad: Sensibilidad
  cliente_nombre: string | null
  notas: string | null
  activa: number
  has_logo: boolean
}

export const marcasApi = {
  list: () => api.get<Marca[]>('/marcas/'),
  create: (data: Omit<Marca, 'id' | 'activa' | 'has_logo'>) => api.post<Marca>('/marcas/', data),
  update: (id: string, data: Partial<Omit<Marca, 'id' | 'activa' | 'has_logo'>>) =>
    api.put<Marca>(`/marcas/${id}`, data),
  remove: (id: string) => api.delete(`/marcas/${id}`),
  uploadLogo: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/marcas/${id}/logo`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  logoPath: (id: string) => `/marcas/${id}/logo`,
}

// ── Alertas ───────────────────────────────────────────────────────────────────
export type EstadoAlerta = 'nueva' | 'revisada' | 'en_oposicion' | 'descartada'

export interface Alerta {
  id: string
  marca_vigilada_id: string
  solicitud_id: string
  score_total: number
  score_denominativo: number
  score_clase: number
  score_figurativo: number | null
  explicacion_ia: string | null
  fecha_limite_oposicion: string | null
  dias_habiles_restantes: number | null
  estado: EstadoAlerta
  borrador_oposicion?: string | null
  borrador_generado_at?: string | null
  denominacion_solicitada: string | null
  expediente: string | null
  solicitante: string | null
  clases_niza: number[] | null
  boletin_numero: number | null
  denominacion_vigilada: string | null
}

export const alertasApi = {
  list: (estado?: EstadoAlerta) =>
    api.get<Alerta[]>('/alertas/', { params: estado ? { estado } : {} }),
  updateEstado: (id: string, estado: EstadoAlerta) =>
    api.patch<Alerta>(`/alertas/${id}/estado`, { estado }),
  requestBorrador: (id: string) => api.post<Alerta>(`/alertas/${id}/borrador`),
}

// ── Boletines ─────────────────────────────────────────────────────────────────
export interface Boletin {
  id: string
  numero: number
  fecha_publicacion: string
  paginas: number | null
  total_solicitudes: number | null
  procesado: boolean
  error_msg: string | null
}

export const boletinesApi = {
  list: () => api.get<Boletin[]>('/boletines/'),
  triggerIngest: () => api.post('/boletines/ingest'),
}

// ── Billing ───────────────────────────────────────────────────────────────────
export interface TierInfo {
  tier: string
  subscription_active: boolean
  trial_ends_at: string | null
  draft_credits: number
  marca_limit: number
}

export const billingApi = {
  tier: () => api.get<TierInfo>('/billing/tier'),
  checkout: (tier: string) =>
    api.post<{ checkout_url: string }>('/billing/checkout', { tier }),
  portal: () => api.post<{ portal_url: string }>('/billing/portal'),
}
