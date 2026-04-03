import { Link } from 'react-router-dom'

type Props = {
  sportLabel: string
}

export function SportHiddenInUiMessage({ sportLabel }: Props) {
  return (
    <div className="rounded-xl border border-app-line bg-app-card p-6 text-sm text-app-fg shadow-sm">
      <p className="font-medium text-violet-950">
        Este run es de <span className="font-mono">{sportLabel}</span>, oculto en la configuración de la app.
      </p>
      <p className="mt-2 text-app-muted">
        Activa el deporte en{' '}
        <Link to="/system-settings" className="text-app-fg underline underline-offset-2">
          Configuración
        </Link>{' '}
        para ver picks, eventos e interacciones.
      </p>
    </div>
  )
}
