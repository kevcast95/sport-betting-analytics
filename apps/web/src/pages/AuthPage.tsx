import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { DisciplineContract } from '@/components/DisciplineContract'
import { Bt2HelpIcon, Bt2LockIcon } from '@/components/icons/bt2Icons'
import { ensureBt2FontLinks } from '@/lib/bt2Fonts'
import { useUserStore } from '@/store/useUserStore'

type AuthMode = 'login' | 'signup'

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      aria-hidden="true"
      fill="none"
    >
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  )
}

export default function AuthPage({
  defaultMode = 'login',
}: {
  defaultMode?: AuthMode
}) {
  const [mode, setMode] = useState<AuthMode>(defaultMode)
  const [mockAuthStatus, setMockAuthStatus] = useState<
    'idle' | 'success'
  >('idle')

  const { isAuthenticated, hasAcceptedContract, hasCompletedDiagnostic, initSession } =
    useUserStore()
  const setHasAcceptedContract = useUserStore(
    (s) => s.setHasAcceptedContract,
  )
  const setOperatorName = useUserStore((s) => s.setOperatorName)

  useEffect(() => {
    ensureBt2FontLinks()
  }, [])

  const monoStyle = useMemo<CSSProperties>(
    () => ({
      fontFamily: `'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`,
    }),
    []
  )

  const onSubmitMock = (e: FormEvent) => {
    e.preventDefault()
    const form = e.currentTarget as HTMLFormElement
    const fd = new FormData(form)
    const name = fd.get('operatorName')
    if (typeof name === 'string' && name.trim()) {
      setOperatorName(name.trim())
    }
    initSession()
    setMockAuthStatus('success')
  }

  const shouldShowContract = isAuthenticated && !hasAcceptedContract

  if (isAuthenticated && hasAcceptedContract) {
    return (
      <Navigate
        to={hasCompletedDiagnostic ? '/v2/sanctuary' : '/v2/diagnostic'}
        replace
      />
    )
  }

  return (
    <div className="relative flex h-full w-[100vw] flex-col overflow-hidden bg-[#f6fafe] text-[#26343d]">
      {/* TopNavBar (V2 only) */}
      <nav className="fixed top-0 z-50 w-full bg-[#f6fafe]/80 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-8 py-4">
          <span className="text-xl font-bold tracking-tighter text-[#26343d]">
            BetTracker 2.0
          </span>
          <div className="flex items-center gap-6">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#eef4fa] text-[#52616a]">
              <Bt2LockIcon className="h-5 w-5" />
            </span>
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#eef4fa] text-[#52616a]">
              <Bt2HelpIcon className="h-5 w-5" />
            </span>
          </div>
        </div>
      </nav>

      <main className="relative flex min-h-0 flex-1 w-full items-center justify-center px-4 pt-20 pb-12">
        {/* Abstract background */}
        <div className="absolute inset-0 -z-0 pointer-events-none overflow-hidden">
          <div className="absolute -top-[10%] -left-[5%] h-[60%] w-[40%] rounded-full bg-[#8B5CF6]/10 blur-[120px]" />
          <div className="absolute -bottom-[10%] -right-[5%] h-[60%] w-[40%] rounded-full bg-[#8B5CF6]/5 blur-[120px]" />
        </div>

        <div className="z-10 w-full max-w-lg">
          <div className="glass-panel rounded-[2rem] border border-[#a4b4be]/20 bg-white/75 p-10 shadow-[0px_20px_40px_rgba(38,52,61,0.06)] backdrop-blur-xl md:p-12">
            <AnimatePresence mode="wait">
              {!isAuthenticated && mode === 'login' && (
                <motion.section
                  key="login"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="mb-10 text-center">
                    <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-full bg-[#e9ddff] text-[#6d3bd7]">
                      <Bt2LockIcon className="h-6 w-6" />
                    </div>
                    <h1 className="mb-2 text-2xl font-bold tracking-tight text-[#26343d]">
                      Acceso a la bóveda de disciplina
                    </h1>
                    <p className="text-xs font-medium tracking-wide text-[#52616a]">
                      AUTENTICACIÓN REQUERIDA
                    </p>
                  </div>

                  <form className="space-y-6" onSubmit={onSubmitMock}>
                    <div className="space-y-2">
                      <label
                        className="px-1 text-[0.70rem] font-semibold uppercase tracking-[0.1em] text-[#52616a]"
                        htmlFor="email"
                      >
                        Correo institucional
                      </label>
                      <input
                        id="email"
                        name="email"
                        type="email"
                        placeholder="operator@vault.digital"
                        required
                        className="w-full rounded-xl border border-transparent bg-[#ddeaf3]/80 px-4 py-3.5 text-sm outline-none transition-all focus:border-[#8B5CF6] focus:bg-[#eef4fa]"
                      />
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between items-center px-1">
                        <label
                          className="text-[0.70rem] font-semibold uppercase tracking-[0.1em] text-[#52616a]"
                          htmlFor="password"
                        >
                          Protocolo de seguridad
                        </label>
                        <a
                          href="#"
                          className="font-mono text-[0.65rem] text-[#8B5CF6] hover:text-[#612aca]"
                          onClick={(e) => e.preventDefault()}
                          style={monoStyle}
                        >
                          ¿Olvidaste la contraseña?
                        </a>
                      </div>
                      <input
                        id="password"
                        name="password"
                        type="password"
                        placeholder="••••••••••••"
                        required
                        className="w-full rounded-xl border border-transparent bg-[#ddeaf3]/80 px-4 py-3.5 text-sm outline-none transition-all focus:border-[#8B5CF6] focus:bg-[#eef4fa]"
                        style={monoStyle}
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-4 text-sm font-semibold tracking-tight text-white shadow-lg shadow-[#8B5CF6]/20 transition-all hover:opacity-90 active:scale-[0.98]"
                    >
                      Entrar al protocolo Sentinel
                    </button>
                  </form>

                  <div className="relative my-8">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-[#a4b4be]/20" />
                    </div>
                    <div className="relative flex justify-center text-[0.65rem] uppercase tracking-widest">
                      <span className="bg-[#fcfcfd] px-4 text-[#52616a]">
                        Verificación externa
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="w-full rounded-xl border border-[#a4b4be]/30 bg-[#ffffff] py-3.5 text-sm font-medium text-[#26343d] transition-colors hover:bg-[#eef4fa] active:scale-[0.98] flex items-center justify-center gap-3"
                    onClick={() => {
                      // POC: sin OAuth real aún.
                      setMode('login')
                      setMockAuthStatus('idle')
                    }}
                  >
                    <GoogleIcon className="h-5 w-5" />
                    Continuar con Google
                  </button>

                  <div className="mt-10 text-center">
                    <p className="text-sm text-[#52616a]">
                      ¿Nuevo operador?{' '}
                      <button
                        type="button"
                        className="ml-1 font-bold text-[#8B5CF6] hover:underline"
                        onClick={() => {
                          setMode('signup')
                          setMockAuthStatus('idle')
                        }}
                      >
                        Crear cuenta
                      </button>
                    </p>
                  </div>

                  {mockAuthStatus === 'success' && (
                    <p
                      className="mt-6 rounded-lg border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-2 text-xs text-[#26343d]"
                      style={monoStyle}
                    >
                      [POC] Inicio de sesión simulado correcto. Completa el
                      Contrato de Disciplina en el modal.
                    </p>
                  )}
                </motion.section>
              )}

              {!isAuthenticated && mode === 'signup' && (
                <motion.section
                  key="signup"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                >
                  <header className="mb-10 space-y-3">
                    <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-[#8B5CF6]/10 px-3 py-1">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#8B5CF6]/15 text-[#8B5CF6]">
                        <Bt2LockIcon className="h-3.5 w-3.5" />
                      </span>
                      <span className="text-[0.65rem] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                        Acceso seguro a la bóveda
                      </span>
                    </div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-[#26343d]">
                      Inicia tu progresión
                    </h1>
                    <p className="text-sm leading-relaxed text-[#52616a]">
                      Registro para gestión profesional de bankroll y evaluación
                      disciplinada del riesgo.
                    </p>
                  </header>

                  <form className="space-y-6" onSubmit={onSubmitMock}>
                    <div className="space-y-2">
                      <label
                        className="ml-1 text-[0.7rem] font-bold uppercase tracking-[0.05em] text-[#52616a]"
                        htmlFor="operatorName"
                      >
                        Nombre del operador
                      </label>
                      <input
                        id="operatorName"
                        name="operatorName"
                        type="text"
                        placeholder="Nombre completo"
                        required
                        className="w-full rounded-xl border border-transparent bg-[#ddeaf3]/80 px-5 py-4 text-[#26343d] outline-none transition-all focus:border-[#8B5CF6] focus:bg-[#eef4fa] placeholder:text-[#a4b4be]/80"
                      />
                    </div>

                    <div className="space-y-2">
                      <label
                        className="ml-1 text-[0.7rem] font-bold uppercase tracking-[0.05em] text-[#52616a]"
                        htmlFor="signupEmail"
                      >
                        Correo seguro
                      </label>
                      <input
                        id="signupEmail"
                        name="email"
                        type="email"
                        placeholder="name@vault.com"
                        required
                        className="w-full rounded-xl border border-transparent bg-[#ddeaf3]/80 px-5 py-4 text-[#26343d] outline-none transition-all focus:border-[#8B5CF6] focus:bg-[#eef4fa] placeholder:text-[#a4b4be]/80"
                      />
                    </div>

                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <label
                          className="ml-1 text-[0.7rem] font-bold uppercase tracking-[0.05em] text-[#52616a]"
                          htmlFor="signupPassword"
                        >
                          Contraseña
                        </label>
                        <input
                          id="signupPassword"
                          name="password"
                          type="password"
                          placeholder="••••••••"
                          required
                          className="w-full rounded-xl border border-transparent bg-[#ddeaf3]/80 px-5 py-4 text-[#26343d] outline-none transition-all focus:border-[#8B5CF6] focus:bg-[#eef4fa] placeholder:text-[#a4b4be]/80"
                          style={monoStyle}
                        />
                      </div>
                      <div className="space-y-2">
                        <label
                          className="ml-1 text-[0.7rem] font-bold uppercase tracking-[0.05em] text-[#52616a]"
                          htmlFor="confirmPassword"
                        >
                          Confirmar contraseña
                        </label>
                        <input
                          id="confirmPassword"
                          name="confirmPassword"
                          type="password"
                          placeholder="••••••••"
                          required
                          className="w-full rounded-xl border border-transparent bg-[#ddeaf3]/80 px-5 py-4 text-[#26343d] outline-none transition-all focus:border-[#8B5CF6] focus:bg-[#eef4fa] placeholder:text-[#a4b4be]/80"
                          style={monoStyle}
                        />
                      </div>
                    </div>

                    <div className="flex items-start gap-3 pt-2">
                      <div className="mt-1">
                        <input
                          id="protocol"
                          name="protocol"
                          type="checkbox"
                          required
                          className="h-5 w-5 rounded-md border-[#a4b4be]/30 text-[#8B5CF6] focus:ring-[#8B5CF6] focus:ring-offset-0 bg-[#eef4fa]"
                        />
                      </div>
                      <label
                        htmlFor="protocol"
                        className="cursor-pointer select-none text-xs leading-relaxed text-[#52616a]"
                      >
                        Acepto el{' '}
                        <span className="font-semibold text-[#26343d] underline decoration-[#8B5CF6]/30">
                          protocolo de adherencia estricta
                        </span>
                        . Entiendo que los datos analíticos se procesan en la
                        bóveda digital segura.
                      </label>
                    </div>

                    <div className="pt-4">
                      <button
                        type="submit"
                        className="w-full rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#612aca] py-4 text-sm font-bold text-white shadow-[0px_10px_20px_rgba(109,59,215,0.2)] transition-all hover:opacity-95 active:scale-[0.98]"
                      >
                        Inicializar perfil de riesgo
                      </button>
                    </div>
                  </form>

                  <div className="mt-8 flex justify-center">
                    <div className="inline-flex items-center gap-3 rounded-full border border-[#a4b4be]/20 bg-[#eef4fa] px-6 py-3 shadow-sm">
                      <div className="h-2 w-2 rounded-full bg-[#fe932c] shadow-[0_0_8px_rgba(145,77,0,0.4)]" />
                      <span className="text-[0.7rem] font-bold uppercase tracking-[0.1em] text-[#52616a]">
                        Estado del sistema: esperando autenticación
                      </span>
                      <span
                        className="text-xs font-semibold"
                        style={{ ...monoStyle, color: '#8B5CF6' }}
                      >
                        LVL 0.00
                      </span>
                    </div>
                  </div>

                  <footer className="mt-10 pt-8 border-t border-[#a4b4be]/20 text-center">
                    <p className="text-sm text-[#52616a]">
                      ¿Ya eres operador?{' '}
                      <button
                        type="button"
                        className="ml-1 font-bold text-[#8B5CF6] hover:underline"
                        onClick={() => {
                          setMode('login')
                          setMockAuthStatus('idle')
                        }}
                      >
                        Iniciar sesión
                      </button>
                    </p>
                  </footer>

                  {mockAuthStatus === 'success' && (
                    <p
                      className="mt-6 rounded-lg border border-[#a4b4be]/30 bg-[#eef4fa] px-3 py-2 text-xs text-[#26343d]"
                      style={monoStyle}
                    >
                      [POC] Registro simulado correcto. Completa el Contrato
                      de Disciplina en el modal.
                    </p>
                  )}
                </motion.section>
              )}

              {isAuthenticated && shouldShowContract && (
                <motion.section
                  key="locked"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  <div className="mb-6 text-center">
                    <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#eef4fa] text-[#8B5CF6]">
                      <Bt2LockIcon className="h-6 w-6" />
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight text-[#26343d]">
                      Acceso bloqueado
                    </h2>
                    <p className="mt-2 text-xs font-medium tracking-wide text-[#52616a]">
                      Completa el Contrato de Disciplina para continuar.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-[#a4b4be]/20 bg-[#eef4fa] px-4 py-4 text-xs leading-relaxed text-[#52616a]">
                    El contrato se mostrará como modal y no podrás cerrarlo
                    hasta completar los 3 axiomas.
                  </div>
                </motion.section>
              )}

              {isAuthenticated && !shouldShowContract && (
                <motion.section
                  key="unlocked"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  <div className="mb-6 text-center">
                    <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#eef4fa] text-[#8B5CF6]">
                      ✓
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight text-[#26343d]">
                      Contrato firmado
                    </h2>
                    <p className="mt-2 text-xs font-medium tracking-wide text-[#52616a]">
                      Puedes continuar con los siguientes pasos del protocolo.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-[#a4b4be]/20 bg-[#eef4fa] px-4 py-4 text-xs leading-relaxed text-[#52616a]">
                    [POC] El acceso al tablero V2 se desbloquea solo tras
                    confirmar los 3 axiomas del contrato.
                  </div>
                </motion.section>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>

      <DisciplineContract
        open={shouldShowContract}
        onCommitted={() => setHasAcceptedContract(true)}
      />
    </div>
  )
}

