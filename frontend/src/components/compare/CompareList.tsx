/** Compare list component showing items in comparison */
import styles from './CompareList.module.css';

interface CompareItem {
  code: string;
  name?: string;
}

interface CompareListProps {
  items: CompareItem[];
  onRemove: (code: string) => void;
  onClear?: () => void;
  maxItems?: number;
}

export function CompareList({
  items,
  onRemove,
  onClear,
  maxItems = 5,
}: CompareListProps) {
  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        比較する銘柄がありません。銘柄を追加してください。
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {items.map((item) => (
        <div key={item.code} className={styles.item}>
          <span className={styles.code}>{item.code}</span>
          {item.name && <span>{item.name}</span>}
          <button
            className={styles.removeBtn}
            onClick={() => onRemove(item.code)}
            aria-label={`${item.code}を削除`}
          >
            &times;
          </button>
        </div>
      ))}
      {onClear && items.length > 1 && (
        <div className={styles.actions}>
          <button className="btn btn-secondary btn-sm" onClick={onClear}>
            全てクリア
          </button>
        </div>
      )}
      {items.length < maxItems && (
        <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)' }}>
          あと{maxItems - items.length}件追加可能
        </span>
      )}
    </div>
  );
}
