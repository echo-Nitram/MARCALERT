import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { boletinesApi } from '../lib/api'
import Spinner from '../components/Spinner'

export default function Boletines() {
  const qc = useQueryClient()

  const { data: boletines = [], isLoading } = useQuery({
    queryKey: ['boletines'],
    queryFn: () => boletinesApi.list().then((r) => r.data),
  })

  const ingestMutation = useMutation({
    mutationFn: () => boletinesApi.triggerIngest(),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ['boletines'] }), 3000),
  })

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Boletines procesados</h1>
          <p className="mt-1 text-sm text-gray-500">
            Historial de boletines del DNPI ingestados por el sistema
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => ingestMutation.mutate()}
          disabled={ingestMutation.isPending}
        >
          {ingestMutation.isPending ? 'Procesando...' : '↻ Verificar nuevo boletín'}
        </button>
      </div>

      {ingestMutation.isSuccess && (
        <div className="mb-4 rounded-md bg-green-50 px-4 py-3 text-sm text-green-700">
          Verificación iniciada en background. Actualizá en unos segundos.
        </div>
      )}

      {isLoading ? (
        <Spinner className="mt-16" />
      ) : boletines.length === 0 ? (
        <div className="card flex flex-col items-center py-16 text-center">
          <span className="text-4xl">📄</span>
          <p className="mt-4 text-lg font-medium text-gray-700">Sin boletines procesados</p>
          <p className="mt-1 text-sm text-gray-500">
            El sistema verifica automáticamente los días hábiles (8h, 12h, 16h).
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Número', 'Fecha', 'Páginas', 'Solicitudes', 'Estado'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {boletines.map((b) => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-semibold text-gray-900">
                    N°{b.numero}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {new Date(b.fecha_publicacion).toLocaleDateString('es-UY')}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {b.paginas ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {b.total_solicitudes ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    {b.error_msg ? (
                      <span className="badge bg-red-100 text-red-700" title={b.error_msg}>
                        Error
                      </span>
                    ) : b.procesado ? (
                      <span className="badge bg-green-100 text-green-700">Procesado</span>
                    ) : (
                      <span className="badge bg-yellow-100 text-yellow-700">Pendiente</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
