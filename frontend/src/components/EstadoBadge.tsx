import type { EstadoAlerta } from '../lib/api'

const MAP: Record<EstadoAlerta, { label: string; cls: string }> = {
  nueva:        { label: 'Nueva',        cls: 'bg-blue-100 text-blue-800' },
  revisada:     { label: 'Revisada',     cls: 'bg-gray-100 text-gray-700' },
  en_oposicion: { label: 'En oposición', cls: 'bg-purple-100 text-purple-800' },
  descartada:   { label: 'Descartada',   cls: 'bg-green-100 text-green-700' },
}

export default function EstadoBadge({ estado }: { estado: EstadoAlerta }) {
  const { label, cls } = MAP[estado] ?? { label: estado, cls: 'bg-gray-100 text-gray-600' }
  return <span className={`badge ${cls}`}>{label}</span>
}
