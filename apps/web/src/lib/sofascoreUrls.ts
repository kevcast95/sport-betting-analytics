/** URL pública del partido en SofaScore (mismo `event_id` que la API). */
export function sofascoreEventUrl(eventId: number): string {
  return `https://www.sofascore.com/event/${eventId}`
}
