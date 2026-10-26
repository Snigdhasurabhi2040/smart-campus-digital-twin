def print_free_rooms(self) -> None:
    for room in self.rooms.values():
        if room.physically_free:
            print(f"{room.name} ({room.room_id}) is free")
