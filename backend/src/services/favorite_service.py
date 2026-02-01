"""Favorite service for managing user favorites."""
from typing import Dict, List, Optional, Tuple

from src.models import Favorite
from src.repositories.etf_repository import ETFRepository
from src.repositories.favorite_repository import FavoriteRepository
from src.repositories.score_cache_repository import ScoreCacheRepository


class FavoriteService:
    """Service for favorite operations."""

    def __init__(
        self,
        favorite_repository: Optional[FavoriteRepository] = None,
        etf_repository: Optional[ETFRepository] = None,
        score_cache_repository: Optional[ScoreCacheRepository] = None,
    ):
        """Initialize favorite service."""
        self.favorite_repository = favorite_repository or FavoriteRepository()
        self.etf_repository = etf_repository or ETFRepository()
        self.score_cache_repository = score_cache_repository or ScoreCacheRepository()

    def get_user_favorites(
        self, user_id: int, perspective: str = "balance", scoring_mode: str = "full"
    ) -> List[Dict]:
        """
        Get all favorites for a user with ETF details and scores.

        Args:
            user_id: User ID
            perspective: Perspective ID for score calculation (balance, dividend, etc.)
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            List of favorite data with ETF information and scores
        """
        favorites = self.favorite_repository.get_by_user_id(user_id)
        result = []

        # Get all ETF codes
        codes = [favorite.etf_code for favorite in favorites]

        # Get scores for the specified perspective
        score_data = self._get_scores_for_perspective(codes, perspective, scoring_mode)

        for favorite in favorites:
            etf = self.etf_repository.get_by_code(favorite.etf_code)
            if etf:
                etf_dict = etf.to_summary_dict()

                # Add score and axis_scores
                scores = score_data.get(favorite.etf_code)
                if scores:
                    etf_dict['score'] = scores['score']
                    etf_dict['axis_scores'] = scores['axis_scores']
                else:
                    etf_dict['score'] = None
                    etf_dict['axis_scores'] = None

                result.append(
                    {
                        "id": favorite.id,
                        "etf_code": favorite.etf_code,
                        "created_at": (
                            favorite.created_at.isoformat()
                            if favorite.created_at
                            else None
                        ),
                        "etf": etf_dict,
                    }
                )

        return result

    def add_favorite(
        self, user_id: int, etf_code: str
    ) -> Tuple[Optional[Favorite], Optional[str]]:
        """
        Add ETF to user's favorites.

        Returns:
            Tuple of (favorite, error_message). Favorite is None if error occurred.
        """
        # Check if ETF exists
        etf = self.etf_repository.get_by_code(etf_code)
        if not etf:
            return None, "指定されたETFが見つかりません"

        # Check if already favorited
        if self.favorite_repository.exists(user_id, etf_code):
            return None, "既にお気に入りに登録されています"

        # Create favorite
        favorite = Favorite(user_id=user_id, etf_code=etf_code)

        try:
            self.favorite_repository.create(favorite)
            return favorite, None
        except Exception as e:
            self.favorite_repository.rollback()
            return None, f"お気に入り登録に失敗しました: {str(e)}"

    def remove_favorite(
        self, user_id: int, etf_code: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Remove ETF from user's favorites.

        Returns:
            Tuple of (success, error_message).
        """
        if not self.favorite_repository.exists(user_id, etf_code):
            return False, "お気に入りに登録されていません"

        try:
            self.favorite_repository.delete_by_user_and_etf(user_id, etf_code)
            return True, None
        except Exception as e:
            self.favorite_repository.rollback()
            return False, f"お気に入り削除に失敗しました: {str(e)}"

    def is_favorited(self, user_id: int, etf_code: str) -> bool:
        """Check if ETF is in user's favorites."""
        return self.favorite_repository.exists(user_id, etf_code)

    def get_favorite_codes(self, user_id: int) -> List[str]:
        """Get list of ETF codes that user has favorited."""
        return self.favorite_repository.get_etf_codes_for_user(user_id)

    def _get_scores_for_perspective(
        self, codes: List[str], perspective: str, scoring_mode: str = 'full'
    ) -> Dict[str, Dict]:
        """Get scores for a specific perspective.

        Args:
            codes: List of ETF codes
            perspective: Perspective ID (balance, dividend, low-cost, etc.)
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            Dict mapping ETF code to dict with score and axis_scores
        """
        return self.score_cache_repository.get_scores_with_axes(
            codes, perspective, scoring_mode
        )
