/** HoldingsList component tests (sortedHoldings) */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { HoldingsList } from '../HoldingsList'
import { Holding } from '../../../api/types'

function makeHolding(
  overrides: Partial<Holding> & { etf_code: string }
): Holding {
  return {
    etf: null,
    quantity: 0,
    average_cost: 0,
    total_cost: 0,
    current_price: 0,
    current_value: 0,
    unrealized_pnl: 0,
    unrealized_pnl_percent: 0,
    total_pnl: 0,
    total_buy_amount: 0,
    total_sell_amount: 0,
    total_pnl_percent: 0,
    ...overrides,
  }
}

// 数量/評価額/保有期間/年率リターンにわざと差異とundefinedを混在させ、
// switch内の数値比較・null合体演算子(?? 0 / ?? -Infinity)・pnlMode分岐を検証する
const holdings: Holding[] = [
  makeHolding({
    etf_code: 'AAA',
    quantity: 100,
    current_value: 5000,
    unrealized_pnl: 500,
    holding_days: 30,
    total_pnl: 800,
    annualized_return: 12.5,
    annualized_return_total: 10,
  }),
  makeHolding({
    etf_code: 'BBB',
    quantity: 50,
    current_value: 8000,
    unrealized_pnl: -200,
    holding_days: undefined,
    total_pnl: 300,
    annualized_return: undefined,
    annualized_return_total: 5,
  }),
  makeHolding({
    etf_code: 'CCC',
    quantity: 200,
    current_value: 3000,
    unrealized_pnl: 1000,
    holding_days: 10,
    total_pnl: -100,
    annualized_return: -5,
    annualized_return_total: undefined,
  }),
]

function renderList(overrides: Record<string, unknown> = {}) {
  return render(
    <HoldingsList
      holdings={holdings}
      isLoading={false}
      error={null}
      onETFClick={vi.fn()}
      {...overrides}
    />
  )
}

// 表示中のコード要素はDOM順で取得できるため、そのまま表示順として利用する
function getDisplayOrder(): string[] {
  return screen
    .getAllByText(/^(AAA|BBB|CCC)$/)
    .map((el) => el.textContent ?? '')
}

describe('HoldingsList - sortedHoldings', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('初期表示はcurrent_value降順でソートされる', () => {
    renderList()
    expect(getDisplayOrder()).toEqual(['BBB', 'AAA', 'CCC'])
  })

  it('銘柄コード列（文字列ソート）を昇順にできる', () => {
    renderList()

    // 初回クリックは常にdesc、再クリックでascにトグルされる
    fireEvent.click(screen.getByRole('columnheader', { name: /^銘柄/ }))
    expect(getDisplayOrder()).toEqual(['CCC', 'BBB', 'AAA'])

    fireEvent.click(screen.getByRole('columnheader', { name: /^銘柄/ }))
    expect(getDisplayOrder()).toEqual(['AAA', 'BBB', 'CCC'])
  })

  it('数量列クリックで降順→再クリックで昇順にトグルする', () => {
    renderList()

    fireEvent.click(screen.getByRole('columnheader', { name: /^数量/ }))
    expect(getDisplayOrder()).toEqual(['CCC', 'AAA', 'BBB']) // 200, 100, 50

    fireEvent.click(screen.getByRole('columnheader', { name: /^数量/ }))
    expect(getDisplayOrder()).toEqual(['BBB', 'AAA', 'CCC']) // 50, 100, 200
  })

  it('保有期間がundefinedの銘柄は0として扱われ降順ソートで最下位になる', () => {
    renderList()

    fireEvent.click(screen.getByRole('columnheader', { name: /^保有期間/ }))
    // AAA:30, CCC:10, BBB:undefined(=>0)
    expect(getDisplayOrder()).toEqual(['AAA', 'CCC', 'BBB'])
  })

  it('年率リターン(pnlMode=current)がundefinedの銘柄は最下位になる', () => {
    renderList()

    fireEvent.click(screen.getByRole('columnheader', { name: /^年率リターン/ }))
    // AAA:12.5, CCC:-5, BBB:undefined(=>-Infinity)
    expect(getDisplayOrder()).toEqual(['AAA', 'CCC', 'BBB'])
  })

  it('pnlModeをトータルに切り替えると年率リターンはannualized_return_totalで判定される', () => {
    renderList()

    fireEvent.click(
      screen.getByRole('button', { name: 'トータルの損益を表示' })
    )
    fireEvent.click(screen.getByRole('columnheader', { name: /^年率リターン/ }))
    // total: AAA:10, BBB:5, CCC:undefined(=>-Infinity)
    expect(getDisplayOrder()).toEqual(['AAA', 'BBB', 'CCC'])
  })
})
