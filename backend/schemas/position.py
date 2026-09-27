from datetime import datetime

from pydantic import BaseModel, Field


# Ce que le client envoie : Pydantic valide les types et les bornes.
class PositionIn(BaseModel):
    vehicle_id: str = Field(min_length=1, max_length=50)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


# Ce que l'API renvoie : on ajoute un horodatage côté serveur.
class PositionOut(PositionIn):
    recorded_at: datetime
