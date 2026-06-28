import { Link, useLocation } from 'react-router-dom'

export default function BillingResult() {
  const loc = useLocation()
  const success = loc.pathname.includes('success')

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="card max-w-sm w-full p-10 text-center">
        <div className="text-5xl mb-4">{success ? '✅' : '❌'}</div>
        <h1 className="text-xl font-bold text-gray-900 mb-2">
          {success ? '¡Suscripción activada!' : 'Pago cancelado'}
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          {success
            ? 'Tu plan ya está activo. Podés empezar a vigilar tus marcas.'
            : 'No se procesó ningún cobro. Podés intentarlo nuevamente cuando quieras.'}
        </p>
        <Link to={success ? '/alertas' : '/billing'} className="btn-primary inline-block">
          {success ? 'Ir al dashboard' : 'Volver a planes'}
        </Link>
      </div>
    </div>
  )
}
