/** FilterPanel component tests */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { FilterPanel } from '../FilterPanel'
import * as api from '../../../api'

vi.mock('../../../api', () => ({
  getCategories: vi.fn(),
  getTags: vi.fn(),
}))

const mockCategories = [
  { id: 1, name: '国内株式', description: null, sort_order: 1 },
  { id: 2, name: '海外株式', description: null, sort_order: 2 },
]

const mockTags = [
  { id: 1, name: 'TOPIX連動', color: '#3B82F6' },
  { id: 2, name: '高配当', color: '#10B981' },
]

describe('FilterPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getCategories).mockResolvedValue(mockCategories)
    vi.mocked(api.getTags).mockResolvedValue(mockTags)
  })

  it('ローディング中は読み込み中と表示', () => {
    vi.mocked(api.getCategories).mockReturnValue(new Promise(() => {}))
    vi.mocked(api.getTags).mockReturnValue(new Promise(() => {}))

    render(<FilterPanel onFilter={vi.fn()} onSearch={vi.fn()} />)
    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
  })

  it('カテゴリが表示される', async () => {
    render(<FilterPanel onFilter={vi.fn()} onSearch={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('国内株式')).toBeInTheDocument()
      expect(screen.getByText('海外株式')).toBeInTheDocument()
    })
  })

  it('タグが表示される', async () => {
    render(<FilterPanel onFilter={vi.fn()} onSearch={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('TOPIX連動')).toBeInTheDocument()
      expect(screen.getByText('高配当')).toBeInTheDocument()
    })
  })

  it('カテゴリ選択/解除が動作する', async () => {
    render(<FilterPanel onFilter={vi.fn()} onSearch={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('国内株式')).toBeInTheDocument()
    })

    const categoryBtn = screen.getByText('国内株式')
    fireEvent.click(categoryBtn)
    expect(categoryBtn.closest('button')?.className).toContain('active')

    fireEvent.click(categoryBtn)
    expect(categoryBtn.closest('button')?.className).not.toContain('active')
  })

  it('タグ選択/解除が動作する', async () => {
    render(<FilterPanel onFilter={vi.fn()} onSearch={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('TOPIX連動')).toBeInTheDocument()
    })

    const tagBtn = screen.getByText('TOPIX連動')
    fireEvent.click(tagBtn)
    expect(tagBtn.closest('button')?.className).toContain('active')

    fireEvent.click(tagBtn)
    expect(tagBtn.closest('button')?.className).not.toContain('active')
  })

  it('カテゴリ選択で即座にonFilterが呼ばれる', async () => {
    const handleFilter = vi.fn()
    render(<FilterPanel onFilter={handleFilter} onSearch={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('国内株式')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('国内株式'))

    expect(handleFilter).toHaveBeenCalledWith({ category_id: 1 })
  })

  it('クリアボタンでフィルターがリセットされる', async () => {
    const handleFilter = vi.fn()
    render(<FilterPanel onFilter={handleFilter} onSearch={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('クリア')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('クリア'))
    expect(handleFilter).toHaveBeenCalledWith({})
  })

  it('保有中ボタンが表示される', async () => {
    render(
      <FilterPanel onFilter={vi.fn()} onSearch={vi.fn()} holdingsCount={5} />
    )

    await waitFor(() => {
      expect(screen.getByText('保有中(5)')).toBeInTheDocument()
    })
  })

  it('保有中ボタンのクリックでonHoldingsOnlyChangeが呼ばれる', async () => {
    const handleHoldingsOnlyChange = vi.fn()
    render(
      <FilterPanel
        onFilter={vi.fn()}
        onSearch={vi.fn()}
        holdingsOnly={false}
        onHoldingsOnlyChange={handleHoldingsOnlyChange}
        holdingsCount={3}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('保有中(3)')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('保有中(3)'))
    expect(handleHoldingsOnlyChange).toHaveBeenCalledWith(true)
  })

  it('保有中ボタンのON/OFFでアクティブ状態が切り替わる', async () => {
    const { rerender } = render(
      <FilterPanel
        onFilter={vi.fn()}
        onSearch={vi.fn()}
        holdingsOnly={false}
        holdingsCount={2}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('保有中(2)')).toBeInTheDocument()
    })

    // OFF状態ではactiveクラスがない
    expect(
      screen.getByText('保有中(2)').closest('button')?.className
    ).not.toContain('active')

    // ON状態に変更
    rerender(
      <FilterPanel
        onFilter={vi.fn()}
        onSearch={vi.fn()}
        holdingsOnly={true}
        holdingsCount={2}
      />
    )

    // ON状態ではactiveクラスがある
    expect(
      screen.getByText('保有中(2)').closest('button')?.className
    ).toContain('active')
  })

  it('APIエラー時にエラーメッセージ表示', async () => {
    vi.mocked(api.getCategories).mockRejectedValue(new Error('API Error'))

    render(<FilterPanel onFilter={vi.fn()} onSearch={vi.fn()} />)

    await waitFor(() => {
      expect(
        screen.getByText('フィルター情報の取得に失敗しました')
      ).toBeInTheDocument()
    })
  })

  it('初期パラメータが適用される', async () => {
    render(
      <FilterPanel
        onFilter={vi.fn()}
        onSearch={vi.fn()}
        initialParams={{
          category_id: 1,
          tag_ids: [1],
        }}
      />
    )

    await waitFor(() => {
      expect(
        screen.getByText('国内株式').closest('button')?.className
      ).toContain('active')
      expect(
        screen.getByText('TOPIX連動').closest('button')?.className
      ).toContain('active')
    })
  })

  it('クリアボタンで保有中フィルターもリセットされる', async () => {
    const handleHoldingsOnlyChange = vi.fn()
    render(
      <FilterPanel
        onFilter={vi.fn()}
        onSearch={vi.fn()}
        holdingsOnly={true}
        onHoldingsOnlyChange={handleHoldingsOnlyChange}
        holdingsCount={3}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('クリア')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('クリア'))
    expect(handleHoldingsOnlyChange).toHaveBeenCalledWith(false)
  })
})
