import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { marcasApi, type Marca, type Sensibilidad, type TipoMarca } from '../lib/api'
import Spinner from '../components/Spinner'
import AuthImage from '../components/AuthImage'

const CLASES_NIZA = Array.from({ length: 45 }, (_, i) => i + 1)

const SENSIBILIDAD_LABELS: Record<Sensibilidad, string> = {
  bajo:  'Baja (score ≥ 60)',
  medio: 'Media (score ≥ 75)',
  alto:  'Alta (score ≥ 90)',
}

const TIPO_LABELS: Record<TipoMarca, string> = {
  denominativa: 'Denominativa (texto)',
  figurativa:   'Figurativa (logo)',
  mixta:        'Mixta (texto + logo)',
}

interface FormData {
  denominacion: string
  tipo: TipoMarca
  clases_niza: number[]
  sensibilidad: Sensibilidad
  cliente_nombre: string
  notas: string
}

const EMPTY_FORM: FormData = {
  denominacion: '',
  tipo: 'denominativa',
  clases_niza: [],
  sensibilidad: 'medio',
  cliente_nombre: '',
  notas: '',
}

export default function Marcas() {
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Marca | null>(null)
  const [form, setForm] = useState<FormData>(EMPTY_FORM)
  const [error, setError] = useState('')
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const qc = useQueryClient()

  const { data: marcas = [], isLoading } = useQuery({
    queryKey: ['marcas'],
    queryFn: () => marcasApi.list().then((r) => r.data),
  })

  const createMutation = useMutation({
    mutationFn: async (data: FormData) => {
      const res = await marcasApi.create(data)
      if (logoFile) await marcasApi.uploadLogo(res.data.id, logoFile).catch(() => {})
      return res
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['marcas'] }); closeForm() },
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Error al guardar'),
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: FormData }) => {
      const res = await marcasApi.update(id, data)
      if (logoFile) await marcasApi.uploadLogo(id, logoFile).catch(() => {})
      return res
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['marcas'] }); closeForm() },
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Error al guardar'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => marcasApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marcas'] }),
  })

  function openCreate() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setError('')
    setLogoFile(null)
    setLogoPreview(null)
    setShowForm(true)
  }

  function openEdit(m: Marca) {
    setEditing(m)
    setForm({
      denominacion:   m.denominacion,
      tipo:           m.tipo,
      clases_niza:    m.clases_niza,
      sensibilidad:   m.sensibilidad,
      cliente_nombre: m.cliente_nombre ?? '',
      notas:          m.notas ?? '',
    })
    setError('')
    setLogoFile(null)
    setLogoPreview(null)  // existing logo shown via AuthImage below
    setShowForm(true)
  }

  function closeForm() {
    setShowForm(false)
    setEditing(null)
    setLogoFile(null)
    setLogoPreview(null)
  }

  function handleLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setLogoFile(file)
    const reader = new FileReader()
    reader.onload = (ev) => setLogoPreview(ev.target?.result as string)
    reader.readAsDataURL(file)
  }

  function toggleClase(c: number) {
    setForm((f) => ({
      ...f,
      clases_niza: f.clases_niza.includes(c)
        ? f.clases_niza.filter((x) => x !== c)
        : [...f.clases_niza, c].sort((a, b) => a - b),
    }))
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (form.clases_niza.length === 0) {
      setError('Seleccioná al menos una clase de Niza')
      return
    }
    if (editing) {
      updateMutation.mutate({ id: editing.id, data: form })
    } else {
      createMutation.mutate(form)
    }
  }

  const activas = marcas.filter((m) => m.activa === 1)

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cartera de marcas</h1>
          <p className="mt-1 text-sm text-gray-500">{activas.length} marca(s) activa(s) bajo vigilancia</p>
        </div>
        <button className="btn-primary" onClick={openCreate}>
          + Agregar marca
        </button>
      </div>

      {isLoading ? (
        <Spinner className="mt-16" />
      ) : activas.length === 0 ? (
        <div className="card flex flex-col items-center py-16 text-center">
          <span className="text-4xl">🏷️</span>
          <p className="mt-4 text-lg font-medium text-gray-700">Sin marcas vigiladas</p>
          <p className="mt-1 text-sm text-gray-500">Agregá tu primera marca para empezar a vigilarla.</p>
          <button className="btn-primary mt-6" onClick={openCreate}>
            Agregar marca
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {activas.map((m) => (
            <div key={m.id} className="card p-4 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-gray-900 truncate">{m.denominacion}</p>
                  {m.cliente_nombre && (
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{m.cliente_nombre}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {m.has_logo && (
                    <AuthImage
                      url={marcasApi.logoPath(m.id)}
                      alt="logo"
                      className="h-10 w-10 rounded object-contain border border-gray-200 bg-white"
                    />
                  )}
                  <span className="badge bg-gray-100 text-gray-600 text-xs">{TIPO_LABELS[m.tipo].split(' ')[0]}</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-1">
                {m.clases_niza.map((c) => (
                  <span key={c} className="badge bg-brand-50 text-brand-600 text-xs">
                    Cl. {c}
                  </span>
                ))}
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>Sensibilidad: <strong>{SENSIBILIDAD_LABELS[m.sensibilidad].split(' ')[0]}</strong></span>
              </div>
              <div className="flex gap-2 pt-1 border-t border-gray-100">
                <button className="btn-secondary text-xs flex-1" onClick={() => openEdit(m)}>
                  Editar
                </button>
                <button
                  className="btn text-xs border border-red-200 text-red-600 hover:bg-red-50 px-3"
                  onClick={() => { if (confirm('¿Pausar vigilancia?')) deleteMutation.mutate(m.id) }}
                >
                  Pausar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal / formulario */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
            <h2 className="mb-4 text-lg font-semibold">
              {editing ? 'Editar marca' : 'Agregar marca a vigilar'}
            </h2>
            {error && (
              <div className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Denominación *</label>
                <input
                  className="input"
                  value={form.denominacion}
                  onChange={(e) => setForm((f) => ({ ...f, denominacion: e.target.value }))}
                  placeholder="Nombre de la marca"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Tipo</label>
                  <select
                    className="input"
                    value={form.tipo}
                    onChange={(e) => setForm((f) => ({ ...f, tipo: e.target.value as TipoMarca }))}
                  >
                    {Object.entries(TIPO_LABELS).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Sensibilidad</label>
                  <select
                    className="input"
                    value={form.sensibilidad}
                    onChange={(e) => setForm((f) => ({ ...f, sensibilidad: e.target.value as Sensibilidad }))}
                  >
                    {Object.entries(SENSIBILIDAD_LABELS).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>
              </div>
              {(form.tipo === 'figurativa' || form.tipo === 'mixta') && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Logo de la marca <span className="text-gray-400">(PNG/JPG, máx 2 MB)</span>
                  </label>
                  <div className="flex items-center gap-3">
                    {logoPreview ? (
                      <img
                        src={logoPreview}
                        alt="preview"
                        className="h-14 w-14 rounded object-contain border border-gray-200 bg-white"
                      />
                    ) : editing?.has_logo && !logoFile ? (
                      <AuthImage
                        url={marcasApi.logoPath(editing.id)}
                        alt="logo actual"
                        className="h-14 w-14 rounded object-contain border border-gray-200 bg-white"
                      />
                    ) : null}
                    <button
                      type="button"
                      className="btn-secondary text-sm"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {(logoPreview || editing?.has_logo) ? 'Cambiar logo' : 'Subir logo'}
                    </button>
                    {logoPreview && (
                      <button
                        type="button"
                        className="text-xs text-red-500 hover:text-red-700"
                        onClick={() => { setLogoFile(null); setLogoPreview(null) }}
                      >
                        Quitar
                      </button>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="hidden"
                    onChange={handleLogoChange}
                  />
                  <p className="mt-1 text-xs text-gray-400">
                    Habilitará comparación visual con logos del boletín (Capa C — Claude Vision)
                  </p>
                </div>
              )}
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Clases de Niza * <span className="text-gray-400">({form.clases_niza.length} seleccionadas)</span>
                </label>
                <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto rounded-md border border-gray-200 p-2 bg-gray-50">
                  {CLASES_NIZA.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => toggleClase(c)}
                      className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                        form.clases_niza.includes(c)
                          ? 'bg-brand-600 text-white'
                          : 'bg-white text-gray-600 border border-gray-300 hover:border-brand-400'
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Cliente (opcional)</label>
                <input
                  className="input"
                  value={form.cliente_nombre}
                  onChange={(e) => setForm((f) => ({ ...f, cliente_nombre: e.target.value }))}
                  placeholder="Nombre del cliente final"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Notas (opcional)</label>
                <textarea
                  className="input resize-none"
                  rows={2}
                  value={form.notas}
                  onChange={(e) => setForm((f) => ({ ...f, notas: e.target.value }))}
                  placeholder="Información adicional"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  className="btn-primary flex-1"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  {editing ? 'Guardar cambios' : 'Agregar a cartera'}
                </button>
                <button type="button" className="btn-secondary" onClick={closeForm}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
