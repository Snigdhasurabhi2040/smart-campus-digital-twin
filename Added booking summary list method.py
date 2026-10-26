def list_bookings(self) -> None:
    for booking in self.bookings.values():
        print(booking.summary())
