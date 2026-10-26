def building_status(self, building_id: str) -> str:
    if self.graph.is_closed(building_id):
        return f"{building_id} CLOSED"
    return f"{building_id} OPEN"
