from dataclasses import dataclass
import datetime as dt

@dataclass
class Booking:
    booking_id: int
    room_id: str
    title: str
    start: int
    end: int
    weekday: int = None
    date: dt.date = None

    def summary(self) -> str:
        return f"{self.title} {start}-{end}"

@dataclass(frozen=True)
class TimeWindow:
    day: dt.date
    start: int
    end: int
