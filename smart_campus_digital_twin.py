from dataclasses import dataclass

@dataclass
class CampusLocation:
    location_id: str
    name: str
    x: float
    y: float
    kind: str = "building"

@dataclass
class Room:
    room_id: str
    name: str
    building_id: str
    room_type: str
    capacity: int
    in_service: bool = True
    occupied: int = 0
