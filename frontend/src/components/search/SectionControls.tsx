/** Section controls component for TopPage */
import { SortField, SortOrder } from '../../api'
import { PerformancePeriod } from '../../api/types'
import { ViewModeToggle, ViewMode } from './ViewModeToggle'
import { TableDisplayToggle, DisplayMode } from './TableDisplayToggle'
import { ScoringModeToggle, ScoringMode } from './ScoringModeToggle'
import { PerspectiveSelector } from './PerspectiveSelector'
import { SortSelector } from './SortSelector'
import { ReturnTypeToggle, ReturnType } from './ReturnTypeToggle'
import { PeriodSelector } from './PeriodSelector'
import type { PerspectiveKey } from './ETFTableView'
import styles from '../../pages/TopPage.module.css'

interface SectionControlsProps {
  viewMode: ViewMode
  displayMode: DisplayMode
  scoringMode: ScoringMode
  selectedPerspective: PerspectiveKey
  selectedPeriods: PerformancePeriod[]
  returnType: ReturnType
  currentSort: SortField
  currentOrder: SortOrder
  onViewModeChange: (mode: ViewMode) => void
  onDisplayModeChange: (mode: DisplayMode) => void
  onScoringModeChange: (mode: ScoringMode) => void
  onPerspectiveChange: (perspective: PerspectiveKey) => void
  onPeriodsChange: (periods: PerformancePeriod[]) => void
  onReturnTypeChange: (returnType: ReturnType) => void
  onSortChange: (sort: SortField, order: SortOrder) => void
}

export function SectionControls({
  viewMode,
  displayMode,
  scoringMode,
  selectedPerspective,
  selectedPeriods,
  returnType,
  currentSort,
  currentOrder,
  onViewModeChange,
  onDisplayModeChange,
  onScoringModeChange,
  onPerspectiveChange,
  onPeriodsChange,
  onReturnTypeChange,
  onSortChange,
}: SectionControlsProps) {
  return (
    <div className={styles.sectionControls}>
      <ViewModeToggle mode={viewMode} onChange={onViewModeChange} />
      <TableDisplayToggle
        displayMode={displayMode}
        onChange={viewMode === 'card' ? () => {} : onDisplayModeChange}
        disabled={viewMode === 'card'}
      />
      {viewMode === 'card' ? (
        <>
          <ScoringModeToggle
            scoringMode={scoringMode}
            onChange={onScoringModeChange}
            className={styles.scoringModeToggle}
          />
          <PerspectiveSelector
            selectedPerspective={selectedPerspective}
            onChange={onPerspectiveChange}
            className={styles.scoringModeToggle}
          />
          <SortSelector
            sort={currentSort}
            order={currentOrder}
            onSortChange={onSortChange}
          />
        </>
      ) : (
        <>
          {displayMode === 'score' && (
            <>
              <ScoringModeToggle
                scoringMode={scoringMode}
                onChange={onScoringModeChange}
                className={styles.scoringModeToggle}
              />
              <PerspectiveSelector
                selectedPerspective={selectedPerspective}
                onChange={onPerspectiveChange}
                className={styles.scoringModeToggle}
              />
            </>
          )}
          {displayMode === 'trend' && (
            <>
              <ReturnTypeToggle
                returnType={returnType}
                onChange={onReturnTypeChange}
              />
              <PeriodSelector
                selectedPeriods={selectedPeriods}
                onChange={onPeriodsChange}
              />
            </>
          )}
        </>
      )}
    </div>
  )
}
