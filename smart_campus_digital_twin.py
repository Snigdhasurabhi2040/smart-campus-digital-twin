import datetime as dt
import heapq
import math
import re
import time

DAY_NAMES = ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")
MINUTES_PER_DAY = 24 * 60

def yes_no_text(value: bool) -> str:
    return "Yes" if value else "No"

def fmt_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
