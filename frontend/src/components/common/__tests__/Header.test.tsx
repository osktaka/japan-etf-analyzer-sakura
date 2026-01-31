/** Header component tests */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import { Header } from '../Header'
import * as useAuthModule from '../../../hooks/useAuth'
import { AuthContextValue } from '../../../contexts/AuthContext'

vi.mock('../../../hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const mockAuthValue: AuthContextValue = {
  user: {
    id: 1,
    email: 'test@example.com',
    username: 'testuser',
    is_active: true,
    is_admin: false,
    created_at: '2025-01-01',
  },
  isLoading: false,
  isAuthenticated: true,
  isAdmin: false,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  checkAuth: vi.fn(),
}

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuthModule.useAuth).mockReturnValue(mockAuthValue)
  })

  it('ロゴが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.getByText('Japan ETF Analyzer')).toBeInTheDocument()
  })

  it('トップリンクが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    // デスクトップnavとモバイルメニューの両方に存在
    const topLinks = screen.getAllByText('トップ')
    expect(topLinks.length).toBeGreaterThanOrEqual(1)
  })

  it('比較リンクが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    // デスクトップnavとモバイルメニューの両方に存在
    const compareLinks = screen.getAllByText('比較')
    expect(compareLinks.length).toBeGreaterThanOrEqual(1)
  })

  it('認証済みの場合、マイページリンクが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    // デスクトップnavとモバイルメニューの両方に存在
    const mypageLinks = screen.getAllByText('マイページ')
    expect(mypageLinks.length).toBeGreaterThanOrEqual(1)
  })

  it('認証済みの場合、ユーザー名が表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    // デスクトップドロップダウンボタンとモバイルユーザー情報の両方にtestuserが含まれる
    const userElements = screen.getAllByText(/testuser/)
    expect(userElements.length).toBeGreaterThanOrEqual(1)
  })

  it('認証済みの場合、ログアウトボタンが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    // デスクトップドロップダウンとモバイルメニューの両方に存在
    const logoutButtons = screen.getAllByText('ログアウト')
    expect(logoutButtons.length).toBeGreaterThanOrEqual(1)
  })

  it('未認証の場合、ログインリンクが表示される', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      ...mockAuthValue,
      user: null,
      isAuthenticated: false,
    })

    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    // デスクトップnavとモバイルメニューの両方に存在
    const loginLinks = screen.getAllByText('ログイン')
    expect(loginLinks.length).toBeGreaterThanOrEqual(1)
  })

  it('未認証の場合、マイページリンクが表示されない', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      ...mockAuthValue,
      user: null,
      isAuthenticated: false,
    })

    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.queryByText('マイページ')).not.toBeInTheDocument()
  })

  it('ローディング中は認証関連要素が表示されない', () => {
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      ...mockAuthValue,
      isLoading: true,
    })

    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.queryByText('ログイン')).not.toBeInTheDocument()
    expect(screen.queryByText('ログアウト')).not.toBeInTheDocument()
    expect(screen.queryByText('マイページ')).not.toBeInTheDocument()
  })

  it('ログアウトボタンクリックでlogoutが呼ばれる', async () => {
    const mockLogout = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useAuthModule.useAuth).mockReturnValue({
      ...mockAuthValue,
      logout: mockLogout,
    })

    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )

    // デスクトップドロップダウンのログアウトボタン（最初の要素）をクリック
    const logoutButtons = screen.getAllByText('ログアウト')
    fireEvent.click(logoutButtons[0])
    expect(mockLogout).toHaveBeenCalled()
  })

  it('現在のルートがアクティブになる', () => {
    render(
      <MemoryRouter initialEntries={['/compare']}>
        <Header />
      </MemoryRouter>
    )

    // デスクトップnavとモバイルメニューの両方に存在
    const compareLinks = screen.getAllByText('比較')
    // 少なくとも1つがactiveクラスを持つ
    const hasActive = compareLinks.some((link) =>
      link.className.includes('active')
    )
    expect(hasActive).toBe(true)
  })

  describe('モバイルメニュー', () => {
    it('ハンバーガーボタンが表示される', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      const hamburgerButton = screen.getByRole('button', {
        name: 'メニューを開く',
      })
      expect(hamburgerButton).toBeInTheDocument()
    })

    it('ハンバーガーボタンにaria-expanded属性がある', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      const hamburgerButton = screen.getByRole('button', {
        name: 'メニューを開く',
      })
      expect(hamburgerButton).toHaveAttribute('aria-expanded', 'false')
    })

    it('ハンバーガーボタンクリックでメニューが開く', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      const hamburgerButton = screen.getByRole('button', {
        name: 'メニューを開く',
      })
      fireEvent.click(hamburgerButton)
      expect(hamburgerButton).toHaveAttribute('aria-expanded', 'true')
      expect(hamburgerButton).toHaveAttribute('aria-label', 'メニューを閉じる')
    })

    it('モバイルメニューにrole="menu"属性がある', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      const mobileMenu = screen.getByRole('menu', {
        name: 'モバイルナビゲーション',
      })
      expect(mobileMenu).toBeInTheDocument()
    })

    it('モバイルメニュー内のリンクにrole="menuitem"属性がある', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      const menuItems = screen.getAllByRole('menuitem')
      expect(menuItems.length).toBeGreaterThan(0)
    })

    it('Escapeキーでメニューが閉じる', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      const hamburgerButton = screen.getByRole('button', {
        name: 'メニューを開く',
      })
      fireEvent.click(hamburgerButton)
      expect(hamburgerButton).toHaveAttribute('aria-expanded', 'true')

      fireEvent.keyDown(document, { key: 'Escape' })
      expect(hamburgerButton).toHaveAttribute('aria-expanded', 'false')
    })

    it('認証済みの場合、モバイルメニューにユーザー情報が表示される', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      expect(screen.getByText('testuser でログイン中')).toBeInTheDocument()
    })

    it('未認証の場合、モバイルメニューにログインリンクが表示される', () => {
      vi.mocked(useAuthModule.useAuth).mockReturnValue({
        ...mockAuthValue,
        user: null,
        isAuthenticated: false,
      })

      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      )
      const loginLinks = screen.getAllByText('ログイン')
      expect(loginLinks.length).toBeGreaterThanOrEqual(1)
    })
  })
})
