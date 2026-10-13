import { useEffect, useState, type ReactNode } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { refreshMacro, refreshMarket } from './lib/apiClient'
import { ThemeProvider } from './contexts/ThemeContext'
import { LoginScreen } from './components/auth/LoginScreen'
import { Header, type Screen } from './components/layout/Header'
import { BookScreen } from './components/book/BookScreen'
import { DashboardScreen } from './components/dashboard/DashboardScreen'
import { AnalysisScreen } from './components/analysis/AnalysisScreen'
import { AnalysesScreen } from './components/analysis/AnalysesScreen'
import { SettingsScreen } from './components/settings/SettingsScreen'
import { MacroScreen } from './components/macro/MacroScreen'
import { SizerScreen } from './components/sizer/SizerScreen'

function AppShell() {
  const { session, loading } = useAuth()
  const userId = session?.user.id
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [analysisTicker, setAnalysisTicker] = useState<string | null>(null)
  const [sizerTicker, setSizerTicker] = useState<string | null>(null)
  // Screens stay mounted (hidden) once opened, so switching back is instant instead of refetching.
  const [visited, setVisited] = useState<ReadonlySet<Screen>>(() => new Set<Screen>(['dashboard']))
  const show = (s: Screen) => {
    setScreen(s)
    setVisited((v) => (v.has(s) ? v : new Set(v).add(s)))
  }
  const openSizer = (t: string) => {
    setSizerTicker(t)
    show('sizer')
  }
  const navigate = (s: Screen) => {
    if (s === 'analysis') setAnalysisTicker(null) // the nav tab always lands on the list
    show(s)
  }
  const openAnalysis = (t: string) => {
    setAnalysisTicker(t)
    show('analysis')
  }
  const kept = (s: Screen, node: ReactNode, hidden = screen !== s) => visited.has(s) && <div hidden={hidden}>{node}</div>

  useEffect(() => {
    if (!userId) return
    refreshMarket().catch((e) => console.warn('Market refresh failed:', e.message))
    refreshMacro().catch((e) => console.warn('Macro refresh failed:', e.message))
  }, [userId])

  if (loading) return null
  if (!session) return <LoginScreen />

  return (
    <>
      <Header screen={screen} onNavigate={navigate} />
      {kept('dashboard', <DashboardScreen onNavigate={navigate} onOpenAnalysis={openAnalysis} />)}
      {kept('book', <BookScreen onOpenAnalysis={openAnalysis} />)}
      {kept('analysis', <AnalysesScreen onOpen={openAnalysis} active={screen === 'analysis' && !analysisTicker} />, screen !== 'analysis' || !!analysisTicker)}
      {screen === 'analysis' && analysisTicker && (
        <AnalysisScreen key={analysisTicker} ticker={analysisTicker} onSize={openSizer} onBack={() => setAnalysisTicker(null)} />
      )}
      {kept('macro', <MacroScreen />)}
      {kept('sizer', <SizerScreen key={sizerTicker ?? ''} initialTicker={sizerTicker} />)}
      {kept('settings', <SettingsScreen onOpenAnalysis={openAnalysis} />)}
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
