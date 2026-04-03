const GOOGLE_FONTS_LINK =
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Geist+Mono:wght@400;500;600&display=swap'

export function ensureBt2FontLinks() {
  if (typeof document === 'undefined') return
  const id = 'bt2-v2-fonts'
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = GOOGLE_FONTS_LINK
  document.head.appendChild(link)
}
