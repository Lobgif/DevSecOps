from fastapi import APIRouter

from schemas.position import PositionIn, PositionOut
from services import position as position_service

router = APIRouter(prefix="/positions", tags=["positions"])


@router.post("", response_model=PositionOut, status_code=201)
async def create_position(position: PositionIn) -> PositionOut:
    return position_service.create_position(position)


@router.get("", response_model=list[PositionOut])
async def list_positions() -> list[PositionOut]:
    return position_service.list_positions()
