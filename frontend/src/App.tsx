import { useEffect, useState } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { listAnalysed, refreshMacro, refreshMarket } from './lib/apiClient'
import { ThemeProvider } from './contexts/ThemeContext'
import { LoginScreen } from './components/auth/LoginScreen'
import { Header, type Screen } from './components/layout/Header'
import { BookScreen } from './components/book/BookScreen'
import { DashboardScreen } from './components/dashboard/DashboardScreen'
import { AnalysisScreen } from './components/analysis/AnalysisScreen'
import { SettingsScreen } from './components/settings/SettingsScreen'
import { MacroScreen } from './components/macro/MacroScreen'

function AppShell() {
  const { session, loading } = useAuth()
  const userId = session?.user.id
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [analysisTicker, setAnalysisTicker] = useState<string | null>(null)
  const openAnalysis = (t: string) => {
    setAnalysisTicker(t)
    setScreen('analysis')
  }

  useEffect(() => {
    if (!userId) return
    refreshMarket().catch((e) => console.warn('Market refresh failed:', e.message))
    refreshMacro().catch((e) => console.warn('Macro refresh failed:', e.message))
    listAnalysed()
      .then((tickers) => setAnalysisTicker((t) => t ?? tickers[0] ?? null))
      .catch((e) => console.warn('Analysis list failed:', e.message))
  }, [userId])

  if (loading) return null
  if (!session) return <LoginScreen />

  return (
    <>
      <Header screen={screen} onNavigate={setScreen} analysisTicker={analysisTicker} />
      {screen === 'dashboard' && <DashboardScreen onNavigate={setScreen} onOpenAnalysis={openAnalysis} />}
      {screen === 'book' && (
        <BookScreen onOpenAnalysis={openAnalysis} />
      )}
      {screen === 'analysis' && analysisTicker && <AnalysisScreen ticker={analysisTicker} />}
      {screen === 'macro' && <MacroScreen />}
      {screen === 'settings' && <SettingsScreen onOpenAnalysis={openAnalysis} />}
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
