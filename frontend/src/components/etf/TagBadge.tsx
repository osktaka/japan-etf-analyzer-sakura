/** Tag badge component */
import { Tag } from '../../api';
import styles from './TagBadge.module.css';

interface TagBadgeProps {
  tag: Tag;
  size?: 'sm' | 'md';
}

export function TagBadge({ tag, size = 'md' }: TagBadgeProps) {
  return (
    <span
      className={`${styles.badge} ${styles[size]}`}
      style={{ backgroundColor: `${tag.color}20`, color: tag.color }}
    >
      {tag.name}
    </span>
  );
}
