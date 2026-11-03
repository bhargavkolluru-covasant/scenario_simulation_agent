import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RecommendationService:
    """Compatibility adapter that forwards selector-owned actions unchanged."""

    async def generate_recommendations(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        selected_actions = state.get("selected_actions") or []
        if not isinstance(selected_actions, list):
            logger.warning(
                "[RecommendationService] selected_actions must be a list"
            )
            return []
        return [item for item in selected_actions if isinstance(item, dict)]
