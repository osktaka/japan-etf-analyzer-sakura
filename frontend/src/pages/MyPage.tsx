/** My page component */
import { useState } from 'react';
import { FavoriteButton } from '../components/actions/FavoriteButton';
import { ETFCard } from '../components/etf/ETFCard';
import { ETFDetailModal } from '../components/modal/ETFDetailModal';
import { useAuth } from '../hooks/useAuth';
import { useFavorites } from '../hooks/useFavorites';
import { ETFSummary } from '../api/types';
import styles from './MyPage.module.css';

export function MyPage() {
  const { user } = useAuth();
  const { favorites, isLoading, error, toggleFavorite } = useFavorites();
  const [selectedETF, setSelectedETF] = useState<ETFSummary | null>(null);

  const handleCardClick = (etf: ETFSummary) => {
    setSelectedETF(etf);
  };

  const handleCloseModal = () => {
    setSelectedETF(null);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>マイページ</h1>
        <p className={styles.welcome}>
          ようこそ、<strong>{user?.username}</strong> さん
        </p>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>お気に入り一覧</h2>

        {isLoading ? (
          <div className={styles.loading}>読み込み中...</div>
        ) : error ? (
          <div className={styles.error}>{error}</div>
        ) : favorites.length === 0 ? (
          <div className={styles.empty}>
            <p>お気に入りに登録されたETFはありません。</p>
            <p className={styles.hint}>
              検索結果やおすすめ一覧からお気に入りに追加できます。
            </p>
          </div>
        ) : (
          <div className={styles.grid}>
            {favorites.map((favorite) => (
              <div key={favorite.id} className={styles.cardWrapper}>
                <ETFCard
                  etf={favorite.etf}
                  onClick={() => handleCardClick(favorite.etf)}
                />
                <div className={styles.favoriteAction}>
                  <FavoriteButton
                    isFavorite={true}
                    onToggle={() => toggleFavorite(favorite.etf_code)}
                    isLoggedIn={true}
                    size="sm"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedETF && (
        <ETFDetailModal code={selectedETF.code} onClose={handleCloseModal} />
      )}
    </div>
  );
}

export default MyPage;
