def count_free_rooms(self) -> int:
    return sum(1 for room in self.rooms.values() if room.physically_free)
