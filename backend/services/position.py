from datetime import datetime, timezone

from repositories import position as position_repository
from schemas.position import PositionIn, PositionOut


def create_position(data: PositionIn) -> PositionOut:
    position = PositionOut(**data.model_dump(), recorded_at=datetime.now(timezone.utc))
    return position_repository.save(position)


def list_positions() -> list[PositionOut]:
    return position_repository.find_all()
