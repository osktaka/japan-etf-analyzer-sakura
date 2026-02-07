import { describe, it, expect } from 'vitest'
import { getMomentumInfo, getMomentumInfoFromAnnualized } from '../momentum'

describe('getMomentumInfo', () => {
  it('上昇加速: 1M>0, 3M>0, 比率>1.45', () => {
    // 1M raw=5% → annual=60%, 3M raw=5% → annual=20%, ratio=3.0>1.45
    const result = getMomentumInfo(5, 5)
    expect(result?.label).toBe('上昇加速')
  })

  it('上昇維持: 1M>0, 3M>0, 比率0.55〜1.45', () => {
    // 1M raw=1% → annual=12%, 3M raw=3% → annual=12%, ratio=1.0
    const result = getMomentumInfo(1, 3)
    expect(result?.label).toBe('上昇維持')
  })

  it('上昇減速: 1M>0, 3M>0, 比率<0.55', () => {
    // 1M raw=0.2% → annual=2.4%, 3M raw=5% → annual=20%, ratio=0.12<0.55
    const result = getMomentumInfo(0.2, 5)
    expect(result?.label).toBe('上昇減速')
  })

  it('反転上昇: 1M>0, 3M≤0', () => {
    const result = getMomentumInfo(2, -1)
    expect(result?.label).toBe('反転上昇')
  })

  it('失速: 1M≤0, 3M>0', () => {
    const result = getMomentumInfo(-1, 2)
    expect(result?.label).toBe('失速')
  })

  it('下降減速: 1M≤0, 3M≤0, 比率<0.55', () => {
    // 1M raw=-0.2% → annual=-2.4%, 3M raw=-5% → annual=-20%, ratio=0.12<0.55
    const result = getMomentumInfo(-0.2, -5)
    expect(result?.label).toBe('下降減速')
  })

  it('下降維持: 1M≤0, 3M≤0, 比率0.55〜1.45', () => {
    // 1M raw=-1% → annual=-12%, 3M raw=-3% → annual=-12%, ratio=1.0
    const result = getMomentumInfo(-1, -3)
    expect(result?.label).toBe('下降維持')
  })

  it('下降加速: 1M≤0, 3M≤0, 比率>1.45', () => {
    // 1M raw=-5% → annual=-60%, 3M raw=-5% → annual=-20%, ratio=3.0>1.45
    const result = getMomentumInfo(-5, -5)
    expect(result?.label).toBe('下降加速')
  })

  it('null入力: rate1mがnullならnull', () => {
    expect(getMomentumInfo(null, 5)).toBeNull()
  })

  it('null入力: rate3mがundefinedならnull', () => {
    expect(getMomentumInfo(3, undefined)).toBeNull()
  })

  it('色情報を含む', () => {
    const result = getMomentumInfo(5, 5)
    expect(result).toHaveProperty('color')
    expect(result).toHaveProperty('bgColor')
  })

  it('ゼロ・ゼロ: 両方0なら下降維持', () => {
    const result = getMomentumInfo(0, 0)
    expect(result?.label).toBe('下降維持')
  })

  it('正・ゼロ: 1M>0, 3M=0なら反転上昇', () => {
    const result = getMomentumInfo(1, 0)
    expect(result?.label).toBe('反転上昇')
  })

  it('負・ゼロ: 1M<0, 3M=0なら下降加速', () => {
    const result = getMomentumInfo(-1, 0)
    expect(result?.label).toBe('下降加速')
  })
})

describe('getMomentumInfoFromAnnualized', () => {
  it('年率化済みの値で上昇加速を判定', () => {
    // ratio = 30/10 = 3.0 > 1.45
    const result = getMomentumInfoFromAnnualized(30, 10)
    expect(result?.label).toBe('上昇加速')
  })

  it('年率化済みの値で上昇維持を判定', () => {
    // ratio = 10/11 = 0.91
    const result = getMomentumInfoFromAnnualized(10, 11)
    expect(result?.label).toBe('上昇維持')
  })

  it('null入力でnullを返す', () => {
    expect(getMomentumInfoFromAnnualized(null, 10)).toBeNull()
    expect(getMomentumInfoFromAnnualized(10, null)).toBeNull()
  })
})
