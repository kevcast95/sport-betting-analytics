export function todayISO() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function rejectReasonLabelEs(reason: string | null | undefined): string {
  const x = String(reason ?? '').trim().toLowerCase()
  if (x === 'lineups_not_ok') return 'alineaciones o datos base incompletos'
  if (x === 'h2h_not_ok') return 'historial H2H insuficiente'
  if (x === 'match_finished') return 'partido ya finalizado'
  return x ? `criterio técnico (${x})` : 'criterios técnicos'
}
