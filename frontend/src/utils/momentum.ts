/** モメンタム（勢い）ラベルのユーティリティ */

export type MomentumLabel =
  | '上昇加速'
  | '上昇維持'
  | '上昇減速'
  | '反転上昇'
  | '失速'
  | '下降減速'
  | '下降維持'
  | '下降加速'

export interface MomentumInfo {
  label: MomentumLabel
  color: string
  bgColor: string
}

/** 「維持」判定の閾値（比率ベース: 3Mに対する1Mの倍率） */
const RATIO_UPPER = 1.45
const RATIO_LOWER = 0.55

export const ALL_MOMENTUM_LABELS: MomentumLabel[] = [
  '上昇加速',
  '上昇維持',
  '上昇減速',
  '反転上昇',
  '失速',
  '下降減速',
  '下降維持',
  '下降加速',
]

export const MOMENTUM_STYLES: Record<
  MomentumLabel,
  { color: string; bgColor: string }
> = {
  上昇加速: { color: '#1ea178', bgColor: '#1ea17838' },
  上昇維持: { color: '#28c08e', bgColor: '#28c08e38' },
  上昇減速: { color: '#7deabe', bgColor: '#7deabe38' },
  反転上昇: { color: '#3b73ed', bgColor: '#3b73ed38' },
  失速: { color: '#f6a823', bgColor: '#f6a82338' },
  下降減速: { color: '#fcaeae', bgColor: '#fcaeae38' },
  下降維持: { color: '#f15757', bgColor: '#f1575738' },
  下降加速: { color: '#e03c3c', bgColor: '#e03c3c38' },
}

/** 年率化済みの1M/3M値からモメンタムを分類 */
function classifyMomentum(annual1m: number, annual3m: number): MomentumLabel {
  if (annual1m > 0 && annual3m > 0) {
    const ratio = annual1m / annual3m
    if (ratio > RATIO_UPPER) return '上昇加速'
    if (ratio < RATIO_LOWER) return '上昇減速'
    return '上昇維持'
  }
  if (annual1m > 0 && annual3m <= 0) return '反転上昇'
  if (annual1m <= 0 && annual3m > 0) return '失速'

  // annual1m <= 0 && annual3m <= 0
  if (annual3m === 0) return annual1m === 0 ? '下降維持' : '下降加速'
  const ratio = annual1m / annual3m
  if (ratio > RATIO_UPPER) return '下降加速'
  if (ratio < RATIO_LOWER) return '下降減速'
  return '下降維持'
}

/**
 * raw回帰上昇率（期間リターン）からモメンタム情報を取得
 * 内部で年率化（1M×12, 3M×4）して比較する
 */
export function getMomentumInfo(
  rate1m: number | null | undefined,
  rate3m: number | null | undefined
): MomentumInfo | null {
  if (rate1m == null || rate3m == null) return null
  return getMomentumInfoFromAnnualized(rate1m * 12, rate3m * 4)
}

/** ラベル文字列から直接スタイルを取得 */
export function getStyleFromLabel(
  label: string | null | undefined
): { color: string; bgColor: string } | null {
  if (!label) return null
  const entry = MOMENTUM_STYLES[label as MomentumLabel]
  return entry ? { color: entry.color, bgColor: entry.bgColor } : null
}

/**
 * 年率化済みの1M/3M回帰上昇率からモメンタム情報を取得
 * AnnualizedReturnCards等、既に年率化されたデータ用
 */
export function getMomentumInfoFromAnnualized(
  annual1m: number | null | undefined,
  annual3m: number | null | undefined
): MomentumInfo | null {
  if (annual1m == null || annual3m == null) return null
  const label = classifyMomentum(annual1m, annual3m)
  return { label, ...MOMENTUM_STYLES[label] }
}

/** 各モメンタムラベルに対応するスコア（0〜100） */
export const MOMENTUM_SCORES: Record<MomentumLabel, number> = {
  上昇加速: 100,
  上昇維持: 85,
  上昇減速: 70,
  反転上昇: 60,
  失速: 40,
  下降減速: 30,
  下降維持: 15,
  下降加速: 0,
}

/** 現金に割り当てるスコア */
export const CASH_SCORE = 50

/** ポートフォリオ全体のモメンタムスコアを加重平均で算出 */
export function calcMomentumScore(
  items: { currentValue: number; momentumLabel: string | null }[],
  cashBalance: number
): number {
  const totalAsset =
    items.reduce((sum, item) => sum + item.currentValue, 0) + cashBalance
  if (totalAsset === 0) return 0

  const FALLBACK_SCORE = 50
  let score = 0
  for (const item of items) {
    const label = item.momentumLabel as MomentumLabel | null
    const labelScore =
      label && label in MOMENTUM_SCORES
        ? MOMENTUM_SCORES[label]
        : FALLBACK_SCORE
    score += (item.currentValue / totalAsset) * labelScore
  }
  score += (cashBalance / totalAsset) * CASH_SCORE
  return score
}

/** スコア（0〜100）に対応するHSLカラーを返す（0=赤, 100=緑） */
export function getMomentumScoreColor(score: number): string {
  const hue = (score / 100) * 120
  return `hsl(${hue}, 70%, 45%)`
}
