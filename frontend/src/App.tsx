import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { LoginScreen } from './components/auth/LoginScreen'
import { Header } from './components/layout/Header'
import { BookScreen } from './components/book/BookScreen'

function AppShell() {
  const { session, loading } = useAuth()

  if (loading) return null
  if (!session) return <LoginScreen />

  return (
    <>
      <Header />
      <BookScreen />
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
