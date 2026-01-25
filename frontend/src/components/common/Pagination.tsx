/** Pagination component */
import styles from './Pagination.module.css'

interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) {
    return null
  }

  const getPageNumbers = (): (number | string)[] => {
    const pages: (number | string)[] = []
    const maxVisible = 5
    const half = Math.floor(maxVisible / 2)

    const end = Math.min(totalPages, Math.max(1, currentPage - half) + maxVisible - 1)
    const start = end - Math.max(1, currentPage - half) + 1 < maxVisible
      ? Math.max(1, end - maxVisible + 1)
      : Math.max(1, currentPage - half)

    if (start > 1) {
      pages.push(1)
      if (start > 2) pages.push('...')
    }

    for (let i = start; i <= end; i++) {
      pages.push(i)
    }

    if (end < totalPages) {
      if (end < totalPages - 1) pages.push('...')
      pages.push(totalPages)
    }

    return pages
  }

  return (
    <nav className={styles.pagination} aria-label="ページネーション">
      <button
        className={styles.button}
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        aria-label="前のページ"
      >
        &lt;
      </button>

      {getPageNumbers().map((page, index) =>
        typeof page === 'number' ? (
          <button
            key={index}
            className={[styles.button, currentPage === page ? styles.active : ''].filter(Boolean).join(' ')}
            onClick={() => onPageChange(page)}
            aria-current={currentPage === page ? 'page' : undefined}
          >
            {page}
          </button>
        ) : (
          <span key={index} className={styles.ellipsis}>
            {page}
          </span>
        )
      )}

      <button
        className={styles.button}
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        aria-label="次のページ"
      >
        &gt;
      </button>
    </nav>
  )
}
