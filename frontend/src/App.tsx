/** Main application component */
import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { Header, Footer, ProtectedRoute, AdminRoute } from './components/common'
import { CompareFloatingButton } from './components/actions'
import { AuthProvider } from './contexts/AuthContext'
import { CompareProvider } from './hooks/useCompareList.tsx'
import { useAuth } from './hooks'
import {
  TopPage,
  ComparePage,
  MarketPage,
  NotesPage,
  NoteDetailPage,
  LoginPage,
  RegisterPage,
  MyPage,
  DemoPage,
  PortfolioPage,
  AdminPage,
  GuideTopPage,
  GuideSearchPage,
  GuideRecommendPage,
  GuideComparePage,
  GuideMypagePage,
  GuideFaqPage,
  GuideTagsPage,
  GuideMomentumPage,
} from './pages'
import { GuideLayout } from './components/guide'
import { ROUTES } from './utils'
import './styles/global.css'

function GoogleAnalytics() {
  const { user, isAdmin, isLoading } = useAuth()
  const isDemo = user?.user_id === 'demo'

  // セッション中のadminログイン/ログアウト対策（GA公式の無効化プロパティ）
  useEffect(() => {
    // eslint-disable-next-line no-extra-semi
    ;(window as unknown as Record<string, unknown>)['ga-disable-G-W5LE9WR4C3'] =
      isAdmin || isDemo
  }, [isAdmin, isDemo])

  // 認証確認中 or 管理者 or デモユーザー → GAを読み込まない
  if (import.meta.env.MODE !== 'production' || isLoading || isAdmin || isDemo)
    return null

  return (
    <Helmet>
      <script
        async
        src="https://www.googletagmanager.com/gtag/js?id=G-W5LE9WR4C3"
      />
      <script>{`
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-W5LE9WR4C3');
      `}</script>
    </Helmet>
  )
}

export default function App() {
  // 開発環境では basename なし、本番環境では /japan-etf-analyzer
  const basename =
    import.meta.env.MODE === 'production' ? '/japan-etf-analyzer' : ''

  return (
    <BrowserRouter basename={basename}>
      <AuthProvider>
        <GoogleAnalytics />
        <CompareProvider>
          <div className="app">
            <Header />
            <main className="container">
              <Routes>
                <Route path={ROUTES.HOME} element={<TopPage />} />
                <Route path={ROUTES.COMPARE} element={<ComparePage />} />
                <Route path={ROUTES.MARKET} element={<MarketPage />} />
                <Route path={ROUTES.NOTES} element={<NotesPage />} />
                <Route path={`${ROUTES.NOTES}/:slug`} element={<NoteDetailPage />} />
                <Route path={ROUTES.DEMO} element={<DemoPage />} />
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
                <Route path={ROUTES.GUIDE} element={<GuideLayout />}>
                  <Route index element={<GuideTopPage />} />
                  <Route path="search" element={<GuideSearchPage />} />
                  <Route path="tags" element={<GuideTagsPage />} />
                  <Route path="momentum" element={<GuideMomentumPage />} />
                  <Route path="recommend" element={<GuideRecommendPage />} />
                  <Route path="compare" element={<GuideComparePage />} />
                  <Route path="mypage" element={<GuideMypagePage />} />
                  <Route path="faq" element={<GuideFaqPage />} />
                </Route>
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
