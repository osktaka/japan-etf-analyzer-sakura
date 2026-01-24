"""Favorite service for managing user favorites."""
from typing import Dict, List, Optional, Tuple

from src.models import Favorite
from src.repositories.etf_repository import ETFRepository
from src.repositories.favorite_repository import FavoriteRepository


class FavoriteService:
    """Service for favorite operations."""

    def __init__(
        self,
        favorite_repository: Optional[FavoriteRepository] = None,
        etf_repository: Optional[ETFRepository] = None,
    ):
        """Initialize favorite service."""
        self.favorite_repository = favorite_repository or FavoriteRepository()
        self.etf_repository = etf_repository or ETFRepository()

    def get_user_favorites(self, user_id: int) -> List[Dict]:
        """
        Get all favorites for a user with ETF details.

        Returns:
            List of favorite data with ETF information
        """
        favorites = self.favorite_repository.get_by_user_id(user_id)
        result = []

        for favorite in favorites:
            etf = self.etf_repository.get_by_code(favorite.etf_code)
            if etf:
                result.append(
                    {
                        "id": favorite.id,
                        "etf_code": favorite.etf_code,
                        "created_at": (
                            favorite.created_at.isoformat()
                            if favorite.created_at
                            else None
                        ),
                        "etf": etf.to_dict(),
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
