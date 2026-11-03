from typing import Any, List


def _contains_entity(value: Any, target: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_entity(item, target) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_entity(item, target) for item in value)
    return value is not None and target in str(value).casefold()


class EntityMatchingService:
    """Match dashboard records using a case-insensitive search across their values."""

    def match(
        self,
        target_entity: str,
        dashboard_rows: List[Any],
    ) -> List[Any]:
        target = target_entity.strip().casefold()
        if not target:
            return []
        return [
            row
            for row in dashboard_rows
            if _contains_entity(row, target)
        ]
