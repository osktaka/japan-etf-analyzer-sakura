/** 売買マーカーのSVGシェイプコンポーネント */

interface MarkerShapeProps {
  cx?: number
  cy?: number
  payload?: { buyMarker?: number; sellMarker?: number }
}

/** 買いマーカー: 上向き三角形（緑） */
export function BuyMarkerShape({ cx = 0, cy = 0, payload }: MarkerShapeProps) {
  if (payload?.buyMarker === undefined) return <g />
  const size = 6
  const points = `${cx},${cy - size} ${cx - size},${cy + size} ${cx + size},${cy + size}`
  return (
    <g style={{ cursor: 'pointer' }}>
      <polygon
        points={points}
        fill="#34d399"
        stroke="#10b981"
        strokeWidth={1}
      />
    </g>
  )
}

/** 売りマーカー: 下向き三角形（赤） */
export function SellMarkerShape({ cx = 0, cy = 0, payload }: MarkerShapeProps) {
  if (payload?.sellMarker === undefined) return <g />
  const size = 6
  // 同日に買い+売り両方ある場合、重複回避でオフセット
  const offsetY =
    payload?.buyMarker !== undefined && payload?.sellMarker !== undefined
      ? 8
      : 0
  const adjustedCy = cy + offsetY
  const points = `${cx},${adjustedCy + size} ${cx - size},${adjustedCy - size} ${cx + size},${adjustedCy - size}`
  return (
    <g style={{ cursor: 'pointer' }}>
      <polygon
        points={points}
        fill="#f87171"
        stroke="#ef4444"
        strokeWidth={1}
      />
    </g>
  )
}
