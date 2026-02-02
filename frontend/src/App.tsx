/** Main application component */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Header, Footer, ProtectedRoute, AdminRoute } from './components/common'
import { CompareFloatingButton } from './components/actions'
import { AuthProvider } from './contexts/AuthContext'
import { CompareProvider } from './hooks/useCompareList.tsx'
import {
  TopPage,
  ComparePage,
  LoginPage,
  RegisterPage,
  MyPage,
  PortfolioPage,
  AdminPage,
} from './pages'
import { ROUTES } from './utils'
import './styles/global.css'

export default function App() {
  // 開発環境では basename なし、本番環境では /japan-etf-analyzer
  const basename =
    import.meta.env.MODE === 'production' ? '/japan-etf-analyzer' : ''

  return (
    <BrowserRouter basename={basename}>
      <AuthProvider>
        <CompareProvider>
          <div className="app">
            <Header />
            <main className="container">
              <Routes>
                <Route path={ROUTES.HOME} element={<TopPage />} />
                <Route path={ROUTES.COMPARE} element={<ComparePage />} />
                <Route path={ROUTES.LOGIN} element={<LoginPage />} />
                <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
                <Route
                  path={ROUTES.MYPAGE}
                  element={
                    <ProtectedRoute>
                      <MyPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path={ROUTES.PORTFOLIO}
                  element={
                    <ProtectedRoute>
                      <PortfolioPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path={ROUTES.ADMIN}
                  element={
                    <AdminRoute>
                      <AdminPage />
                    </AdminRoute>
                  }
                />
              </Routes>
            </main>
            <Footer />
            <CompareFloatingButton />
          </div>
        </CompareProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
