/** Main application component */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Header, Footer, ProtectedRoute } from './components/common'
import { AuthProvider } from './contexts/AuthContext'
import {
  TopPage,
  ComparePage,
  LoginPage,
  RegisterPage,
  MyPage,
  PortfolioPage,
} from './pages'
import { ROUTES } from './utils'
import './styles/global.css'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
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
            </Routes>
          </main>
          <Footer />
        </div>
      </AuthProvider>
    </BrowserRouter>
  )
}
