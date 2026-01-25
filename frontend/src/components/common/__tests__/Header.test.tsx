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
    created_at: '2025-01-01',
  },
  isLoading: false,
  isAuthenticated: true,
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

  it('ホームリンクが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.getByText('ホーム')).toBeInTheDocument()
  })

  it('比較リンクが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.getByText('比較')).toBeInTheDocument()
  })

  it('認証済みの場合、マイページリンクが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.getByText('マイページ')).toBeInTheDocument()
  })

  it('認証済みの場合、ユーザー名が表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.getByText('testuser')).toBeInTheDocument()
  })

  it('認証済みの場合、ログアウトボタンが表示される', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    )
    expect(screen.getByText('ログアウト')).toBeInTheDocument()
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
    expect(screen.getByText('ログイン')).toBeInTheDocument()
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

    fireEvent.click(screen.getByText('ログアウト'))
    expect(mockLogout).toHaveBeenCalled()
  })

  it('現在のルートがアクティブになる', () => {
    render(
      <MemoryRouter initialEntries={['/compare']}>
        <Header />
      </MemoryRouter>
    )

    const compareLink = screen.getByText('比較')
    expect(compareLink.className).toContain('active')
  })
})
