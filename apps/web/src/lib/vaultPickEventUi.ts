/**
 * D-05-019 / T-169: rótulo visible + opacidad según `eventStatus` (CDM) e `isAvailable` (router).
 * No inventar estados: valores crudos vienen del BE.
 */
export type VaultPickEventPresentation = {
  /** null = sin badge (p. ej. mock local). */
  statusLabel: string | null
  badgeClass: string
  dimCard: boolean
}

const BADGE_UNAVAILABLE =
  'rounded-full bg-[#fee2e2] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#9b1c1c]'
const BADGE_FINISHED =
  'rounded-full bg-[#e5e7eb] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#374151]'
const BADGE_INPLAY =
  'rounded-full bg-[#dbeafe] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#1d4ed8]'
const BADGE_SCHEDULED =
  'rounded-full bg-[#ecfdf5] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#065f46]'
const BADGE_UNKNOWN =
  'rounded-full bg-[#f3f4f6] px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#4b5563]'

/**
 * @param isApiPick — solo picks GET /bt2/vault/picks muestran estado de evento.
 */
export function vaultPickEventPresentation(
  eventStatus: string | null | undefined,
  isAvailable: boolean,
  isApiPick: boolean,
): VaultPickEventPresentation {
  if (!isApiPick) {
    return { statusLabel: null, badgeClass: '', dimCard: false }
  }
  if (!isAvailable) {
    return {
      statusLabel: 'No disponible',
      badgeClass: BADGE_UNAVAILABLE,
      dimCard: true,
    }
  }
  const st = (eventStatus ?? '').trim().toLowerCase()
  if (
    st === 'finished' ||
    st === 'complete' ||
    st === 'completed' ||
    st === 'closed'
  ) {
    return {
      statusLabel: 'Finalizado',
      badgeClass: BADGE_FINISHED,
      dimCard: true,
    }
  }
  if (st === 'inplay' || st === 'in_play' || st === 'live') {
    return {
      statusLabel: 'En juego',
      badgeClass: BADGE_INPLAY,
      dimCard: false,
    }
  }
  if (
    st === 'scheduled' ||
    st === 'not_started' ||
    st === '' ||
    st === 'pre_match' ||
    st === 'prematch'
  ) {
    return {
      statusLabel: 'Programado',
      badgeClass: BADGE_SCHEDULED,
      dimCard: false,
    }
  }
  return {
    statusLabel: eventStatus?.trim()
      ? `Estado: ${eventStatus.trim()}`
      : 'Programado',
    badgeClass: BADGE_UNKNOWN,
    dimCard: false,
  }
}
