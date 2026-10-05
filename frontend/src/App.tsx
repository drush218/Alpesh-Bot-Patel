import { useEffect, useState } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { refreshMarket } from './lib/apiClient'
import { ThemeProvider } from './contexts/ThemeContext'
import { LoginScreen } from './components/auth/LoginScreen'
import { Header, type Screen } from './components/layout/Header'
import { BookScreen } from './components/book/BookScreen'
import { DashboardScreen } from './components/dashboard/DashboardScreen'

function AppShell() {
  const { session, loading } = useAuth()
  const userId = session?.user.id
  const [screen, setScreen] = useState<Screen>('dashboard')

  useEffect(() => {
    if (!userId) return
    refreshMarket().catch((e) => console.warn('Market refresh failed:', e.message))
  }, [userId])

  if (loading) return null
  if (!session) return <LoginScreen />

  return (
    <>
      <Header screen={screen} onNavigate={setScreen} />
      {screen === 'dashboard' ? <DashboardScreen /> : <BookScreen />}
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
