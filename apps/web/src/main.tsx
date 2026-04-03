import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/** Asegura que el árbol ocupe el flex de #root (scroll solo dentro de AppLayout). */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <App />
      </div>
    </QueryClientProvider>
  </StrictMode>,
)
