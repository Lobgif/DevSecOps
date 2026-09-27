from schemas.position import PositionOut

# Stockage en mémoire : perdu à chaque redémarrage (PostGIS viendra plus tard).
_positions: list[PositionOut] = []


def save(position: PositionOut) -> PositionOut:
    _positions.append(position)
    return position


def find_all() -> list[PositionOut]:
    return _positions
