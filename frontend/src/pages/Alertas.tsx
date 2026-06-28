import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { alertasApi, type Alerta, type EstadoAlerta } from '../lib/api'
import ScoreBadge from '../components/ScoreBadge'
import EstadoBadge from '../components/EstadoBadge'
import Spinner from '../components/Spinner'

const ESTADOS: { value: EstadoAlerta | ''; label: string }[] = [
  { value: '',             label: 'Todas' },
  { value: 'nueva',        label: 'Nuevas' },
  { value: 'revisada',     label: 'Revisadas' },
  { value: 'en_oposicion', label: 'En oposición' },
  { value: 'descartada',   label: 'Descartadas' },
]

export default function Alertas() {
  const [filtro, setFiltro] = useState<EstadoAlerta | ''>('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const qc = useQueryClient()

  const { data: alertas = [], isLoading } = useQuery({
    queryKey: ['alertas', filtro],
    queryFn: () => alertasApi.list(filtro || undefined).then((r) => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: EstadoAlerta }) =>
      alertasApi.updateEstado(id, estado),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alertas'] }),
  })

  const borradorMutation = useMutation({
    mutationFn: (id: string) => alertasApi.requestBorrador(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alertas'] }),
  })

  const nuevas = alertas.filter((a) => a.estado === 'nueva').length

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alertas de colisión</h1>
          <p className="mt-1 text-sm text-gray-500">
            Colisiones detectadas entre el boletín y su cartera de marcas
          </p>
        </div>
        {nuevas > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-800">
            {nuevas} nueva{nuevas !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Filtros */}
      <div className="mb-4 flex gap-2">
        {ESTADOS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setFiltro(value)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              filtro === value
                ? 'bg-brand-600 text-white'
                : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Lista */}
      {isLoading ? (
        <Spinner className="mt-16" />
      ) : alertas.length === 0 ? (
        <div className="card mt-8 flex flex-col items-center py-16 text-center">
          <span className="text-4xl">✅</span>
          <p className="mt-4 text-lg font-medium text-gray-700">Sin alertas</p>
          <p className="mt-1 text-sm text-gray-500">
            {filtro ? 'No hay alertas con ese estado.' : 'No hay colisiones detectadas todavía.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alertas.map((alerta) => (
            <AlertaCard
              key={alerta.id}
              alerta={alerta}
              expanded={expanded === alerta.id}
              onToggle={() => setExpanded(expanded === alerta.id ? null : alerta.id)}
              onEstado={(estado) => updateMutation.mutate({ id: alerta.id, estado })}
              onBorrador={() => borradorMutation.mutate(alerta.id)}
              loading={updateMutation.isPending || borradorMutation.isPending}
            />
          ))}
        </div>
      )}

      <p className="mt-6 text-xs text-gray-400">
        * Las fechas límite de oposición son estimadas (30 días hábiles desde publicación del boletín).
        Verificar siempre con DNPI y Ley 17.011.
      </p>
    </div>
  )
}

interface CardProps {
  alerta: Alerta
  expanded: boolean
  onToggle: () => void
  onEstado: (e: EstadoAlerta) => void
  onBorrador: () => void
  loading: boolean
}

function AlertaCard({ alerta, expanded, onToggle, onEstado, onBorrador, loading }: CardProps) {
  const urgent =
    alerta.dias_habiles_restantes !== null && alerta.dias_habiles_restantes <= 10

  return (
    <div className={`card overflow-hidden transition-shadow ${urgent && alerta.estado === 'nueva' ? 'border-red-300 ring-1 ring-red-200' : ''}`}>
      {/* Fila principal */}
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-4 p-4 text-left hover:bg-gray-50 transition-colors"
      >
        <ScoreBadge score={alerta.score_total} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-900 truncate">
              {alerta.denominacion_solicitada ?? '—'}
            </span>
            <span className="text-gray-400">vs</span>
            <span className="font-medium text-brand-600 truncate">
              {alerta.denominacion_vigilada ?? '—'}
            </span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 flex-wrap">
            <span>Exp. {alerta.expediente}</span>
            {alerta.boletin_numero && <span>Bol. {alerta.boletin_numero}</span>}
            {alerta.clases_niza && (
              <span>Clases: {alerta.clases_niza.join(', ')}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {alerta.fecha_limite_oposicion && (
            <div className={`text-right text-xs ${urgent ? 'text-red-600 font-semibold' : 'text-gray-500'}`}>
              <div>Límite{urgent ? ' ⚠️' : ''}</div>
              <div>{new Date(alerta.fecha_limite_oposicion).toLocaleDateString('es-UY')}</div>
              {alerta.dias_habiles_restantes !== null && (
                <div>{alerta.dias_habiles_restantes} días háb.</div>
              )}
            </div>
          )}
          <EstadoBadge estado={alerta.estado} />
          <span className="text-gray-400">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Detalle expandido */}
      {expanded && (
        <div className="border-t border-gray-100 bg-gray-50 p-4 space-y-4">
          {/* Scores desglosados */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="rounded-md bg-white p-3 shadow-sm">
              <div className="text-xs text-gray-500">Fonético</div>
              <div className="mt-1 text-lg font-bold text-gray-800">
                {alerta.score_denominativo.toFixed(0)}
              </div>
            </div>
            <div className="rounded-md bg-white p-3 shadow-sm">
              <div className="text-xs text-gray-500">Clases Niza</div>
              <div className="mt-1 text-lg font-bold text-gray-800">
                {alerta.score_clase.toFixed(0)}
              </div>
            </div>
            <div className="rounded-md bg-white p-3 shadow-sm">
              <div className="text-xs text-gray-500">Total</div>
              <div className="mt-1 text-lg font-bold text-brand-600">
                {alerta.score_total.toFixed(0)}
              </div>
            </div>
          </div>

          {/* Solicitante */}
          {alerta.solicitante && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Solicitante:</span> {alerta.solicitante}
            </p>
          )}

          {/* Explicación IA */}
          {alerta.explicacion_ia && (
            <div className="rounded-md border border-blue-100 bg-blue-50 p-3">
              <p className="text-xs font-semibold text-blue-700 mb-1">Análisis IA</p>
              <p className="text-sm text-blue-900">{alerta.explicacion_ia}</p>
            </div>
          )}

          {/* Borrador de oposición */}
          {alerta.borrador_oposicion && (
            <div className="rounded-md border border-purple-100 bg-purple-50 p-3">
              <p className="text-xs font-semibold text-purple-700 mb-2">Borrador de oposición</p>
              <pre className="whitespace-pre-wrap text-xs text-purple-900 font-sans leading-relaxed">
                {alerta.borrador_oposicion}
              </pre>
            </div>
          )}

          {/* Acciones */}
          <div className="flex flex-wrap gap-2 pt-1">
            {alerta.estado === 'nueva' && (
              <>
                <button
                  className="btn-secondary text-xs"
                  onClick={() => onEstado('revisada')}
                  disabled={loading}
                >
                  Marcar revisada
                </button>
                <button
                  className="btn-primary text-xs"
                  onClick={() => onEstado('en_oposicion')}
                  disabled={loading}
                >
                  Presentar oposición
                </button>
                <button
                  className="btn text-xs border border-gray-300 bg-white text-gray-500 hover:bg-gray-50"
                  onClick={() => onEstado('descartada')}
                  disabled={loading}
                >
                  Descartar
                </button>
              </>
            )}
            {alerta.estado === 'revisada' && (
              <>
                <button
                  className="btn-primary text-xs"
                  onClick={() => onEstado('en_oposicion')}
                  disabled={loading}
                >
                  Presentar oposición
                </button>
                <button
                  className="btn text-xs border border-gray-300 bg-white text-gray-500"
                  onClick={() => onEstado('descartada')}
                  disabled={loading}
                >
                  Descartar
                </button>
              </>
            )}
            {alerta.estado === 'en_oposicion' && !alerta.borrador_oposicion && (
              <button
                className="btn-secondary text-xs"
                onClick={onBorrador}
                disabled={loading}
              >
                Generar borrador de oposición (IA)
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
