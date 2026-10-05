import { useEffect, useState } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { listAnalysed, refreshMarket } from './lib/apiClient'
import { ThemeProvider } from './contexts/ThemeContext'
import { LoginScreen } from './components/auth/LoginScreen'
import { Header, type Screen } from './components/layout/Header'
import { BookScreen } from './components/book/BookScreen'
import { DashboardScreen } from './components/dashboard/DashboardScreen'
import { AnalysisScreen } from './components/analysis/AnalysisScreen'

function AppShell() {
  const { session, loading } = useAuth()
  const userId = session?.user.id
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [analysisTicker, setAnalysisTicker] = useState<string | null>(null)

  useEffect(() => {
    if (!userId) return
    refreshMarket().catch((e) => console.warn('Market refresh failed:', e.message))
    listAnalysed()
      .then((tickers) => setAnalysisTicker((t) => t ?? tickers[0] ?? null))
      .catch((e) => console.warn('Analysis list failed:', e.message))
  }, [userId])

  if (loading) return null
  if (!session) return <LoginScreen />

  return (
    <>
      <Header screen={screen} onNavigate={setScreen} analysisTicker={analysisTicker} />
      {screen === 'dashboard' && <DashboardScreen />}
      {screen === 'book' && (
        <BookScreen
          onOpenAnalysis={(t) => {
            setAnalysisTicker(t)
            setScreen('analysis')
          }}
        />
      )}
      {screen === 'analysis' && analysisTicker && <AnalysisScreen ticker={analysisTicker} />}
    </>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </ThemeProvider>
  )
}
