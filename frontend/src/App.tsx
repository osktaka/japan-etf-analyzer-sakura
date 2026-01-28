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
  return (
    <BrowserRouter>
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
