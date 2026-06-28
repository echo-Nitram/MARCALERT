import { useQuery, useMutation } from '@tanstack/react-query'
import { billingApi } from '../lib/api'
import Spinner from '../components/Spinner'

const PLANES = [
  {
    tier: 'starter',
    nombre: 'Starter',
    precio: 'USD 29/mes',
    marcas: 'hasta 10 marcas',
    features: ['Alertas automáticas', 'Email de notificación', 'Dashboard web'],
  },
  {
    tier: 'pro',
    nombre: 'Pro',
    precio: 'USD 79/mes',
    marcas: 'hasta 50 marcas',
    features: ['Todo lo de Starter', 'Filtros avanzados', 'Métricas de cartera'],
  },
  {
    tier: 'estudio',
    nombre: 'Estudio',
    precio: 'USD 199/mes',
    marcas: 'Marcas ilimitadas',
    features: ['Todo lo de Pro', 'Borradores de oposición (IA)', 'Claude Vision para logos'],
    destacado: true,
  },
]

export default function Billing() {
  const { data: tier, isLoading } = useQuery({
    queryKey: ['billing-tier'],
    queryFn: () => billingApi.tier().then((r) => r.data),
  })

  const checkoutMutation = useMutation({
    mutationFn: (t: string) => billingApi.checkout(t).then((r) => r.data),
    onSuccess: (data) => { window.location.href = data.checkout_url },
  })

  const portalMutation = useMutation({
    mutationFn: () => billingApi.portal().then((r) => r.data),
    onSuccess: (data) => { window.location.href = data.portal_url },
  })

  if (isLoading) return <Spinner className="mt-24" />

  const tierActual = tier?.tier ?? 'starter'
  const trialEnds = tier?.trial_ends_at
    ? new Date(tier.trial_ends_at)
    : null
  const enTrial = trialEnds && trialEnds > new Date()

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Suscripción</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestioná tu plan y facturación
        </p>
      </div>

      {/* Plan actual */}
      <div className="card mb-8 p-5 flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">Plan actual</p>
          <p className="text-xl font-bold text-brand-600 capitalize">{tierActual}</p>
          {enTrial && (
            <p className="mt-1 text-sm text-orange-600">
              Período de prueba hasta {trialEnds!.toLocaleDateString('es-UY')}
            </p>
          )}
          {tier && (
            <p className="mt-1 text-sm text-gray-500">
              Límite: {tier.marca_limit >= 999999 ? 'ilimitadas' : tier.marca_limit} marcas
              {tier.draft_credits > 0 && ` · ${tier.draft_credits} crédito(s) de borrador`}
            </p>
          )}
        </div>
        {tier?.subscription_active && (
          <button
            className="btn-secondary text-sm"
            onClick={() => portalMutation.mutate()}
            disabled={portalMutation.isPending}
          >
            {portalMutation.isPending ? 'Redirigiendo...' : 'Gestionar facturación'}
          </button>
        )}
      </div>

      {/* Tabla de planes */}
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Planes disponibles</h2>
      <div className="grid gap-4 md:grid-cols-3">
        {PLANES.map((plan) => {
          const esCurrent = plan.tier === tierActual
          return (
            <div
              key={plan.tier}
              className={`card p-5 flex flex-col gap-4 relative ${
                plan.destacado ? 'border-brand-600 ring-2 ring-brand-600' : ''
              }`}
            >
              {plan.destacado && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="badge bg-brand-600 text-white text-xs px-3 py-1">Recomendado</span>
                </div>
              )}
              <div>
                <p className="font-bold text-gray-900 text-lg">{plan.nombre}</p>
                <p className="text-2xl font-extrabold text-brand-600 mt-1">{plan.precio}</p>
                <p className="text-sm text-gray-500 mt-0.5">{plan.marcas}</p>
              </div>
              <ul className="flex-1 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="text-green-500 mt-0.5">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              {esCurrent ? (
                <div className="btn border border-brand-200 bg-brand-50 text-brand-600 cursor-default text-sm">
                  Plan actual
                </div>
              ) : (
                <button
                  className={plan.destacado ? 'btn-primary text-sm' : 'btn-secondary text-sm'}
                  onClick={() => checkoutMutation.mutate(plan.tier)}
                  disabled={checkoutMutation.isPending}
                >
                  {checkoutMutation.isPending ? 'Redirigiendo...' : `Suscribirse a ${plan.nombre}`}
                </button>
              )}
            </div>
          )
        })}
      </div>

      <p className="mt-8 text-xs text-gray-400 text-center">
        Los precios son en dólares estadounidenses. Podés cancelar en cualquier momento
        desde el portal de facturación.
      </p>
    </div>
  )
}
