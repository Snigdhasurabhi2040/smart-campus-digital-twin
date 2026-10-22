"""
SMART CAMPUS DIGITAL TWIN
=========================

A self-contained, menu-driven Python application for managing a campus:
rooms, timetables, walking routes, sensors, energy use and alerts.

Data structures / algorithms used
---------------------------------
1.  Graph (adjacency list)          - campus map and walkable pathways
2.  Hash maps (dict)                - fast lookup of locations, rooms, bookings
3.  Priority queue (heapq)          - alerts, most urgent first
4.  KD-tree                         - nearest campus location to a coordinate
5.  Disjoint Set Union (Union-Find) - campus connectivity
6.  Fenwick tree (BIT)              - building energy totals and range queries
7.  A* and Dijkstra                 - A*: shortest route; Dijkstra: nearest free room
8.  Kruskal MST                     - shortest set of pathways that keeps the campus connected
9.  KMP string search               - text search over room / building names
10. Interval-overlap checks         - timetable clash detection

Room rules (important)
----------------------
A room is AVAILABLE only when the WHOLE room is free:
  * its building is open (not closed for construction etc.), AND
  * it is in service (not under maintenance), AND
  * nobody is inside it, AND
  * no booked class/session is running in it right now.
A room can also be checked for any future time window.

Blocked pathways vs closed buildings
------------------------------------
* A PATHWAY block closes one road between two locations (road work, flooding...).
  The buildings stay open; routes simply go around it.
* A BUILDING closure (e.g. under construction) closes the whole building: routes
  cannot enter or pass through it, and all its rooms become unavailable.

Timetable
---------
* Weekly bookings repeat every week on chosen weekdays (normal class timetable).
* One-off bookings are for a single calendar date.
* Two bookings for the same room may never overlap (back-to-back is fine:
  10:00-11:00 followed by 11:00-12:00).
* Walk-in sessions are booked for a duration, so they can never run into the
  next scheduled class.
* A simulated clock lets you test any day/time (menu option 15).

Run with:   python smart_campus_digital_twin.py
No third-party packages are needed (Python 3.8+).

Note: sensor readings are simulated; nothing is connected to real hardware,
and data is kept in memory only (it is lost when the program closes).
"""

from __future__ import annotations

import datetime as dt
import heapq
import math
import random
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOM_TYPES = ("classroom", "laboratory")
HIGH_TEMPERATURE_C = 28.0

# Why a pathway (road) or a whole building can be closed.
PATH_BLOCK_REASONS = (
    "Road work / construction on the pathway",
    "Waterlogging / flooding",
    "Event or heavy crowd",
    "Safety hazard (accident, fallen tree, etc.)",
    "Other",
)
BUILDING_CLOSE_REASONS = (
    "Under construction / renovation",
    "Maintenance or repair work",
    "Emergency / safety issue",
    "Closed for an event or holiday",
)

# Alert priority number -> label shown to the user (1 = most urgent).
ALERT_LEVELS = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "INFO"}


DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MINUTES_PER_DAY = 24 * 60


def yes_no_text(value: bool) -> str:
    """Show booleans to users as Yes / No instead of True / False."""
    return "Yes" if value else "No"


def fmt_time(minutes: int) -> str:
    """Minutes after midnight -> 'HH:MM' (1440 shows as 24:00)."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_time(text: str, allow_24: bool = False) -> Optional[int]:
    """
    Parse '14:30', '9:05', '2:30pm', '9am', '12am' into minutes after midnight.
    Returns None if the text is not a valid time. '24:00' is allowed only
    when allow_24 is True (used for 'end of day').
    """
    match = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*", text.lower())
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    suffix = match.group(3)
    if minute > 59:
        return None
    if suffix:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if suffix == "pm" else 0)
    elif hour == 24:
        return MINUTES_PER_DAY if (allow_24 and minute == 0) else None
    if hour > 23:
        return None
    return hour * 60 + minute


def parse_weekday(text: str) -> Optional[int]:
    """'mon', 'Monday', 'thu' ... -> 0..6 (at least 3 letters needed)."""
    text = text.strip().lower()
    if len(text) < 3:
        return None
    for index, name in enumerate(DAY_NAMES):
        if name.lower().startswith(text):
            return index
    return None


def parse_day(text: str, today: dt.date) -> Optional[dt.date]:
    """
    Accepts 'today', 'tomorrow', a weekday name (next such day, today
    included), or a date as YYYY-MM-DD, DD-MM-YYYY or DD/MM/YYYY.
    """
    text = text.strip().lower()
    if text == "today":
        return today
    if text == "tomorrow":
        return today + dt.timedelta(days=1)
    weekday = parse_weekday(text)
    if weekday is not None:
        return today + dt.timedelta(days=(weekday - today.weekday()) % 7)
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# 1. DATA MODELS
# ---------------------------------------------------------------------------

@dataclass
class CampusLocation:
    """A point on the campus map (building, gate, ...)."""
    location_id: str
    name: str
    x: float
    y: float
    kind: str = "building"

    def __post_init__(self) -> None:
        self.location_id = self.location_id.strip().upper()
        self.name = self.name.strip()
        if not self.location_id or not self.name:
            raise ValueError("A location needs a non-empty ID and name.")
        if not (math.isfinite(self.x) and math.isfinite(self.y)):
            raise ValueError("Location coordinates must be finite numbers.")


@dataclass
class Room:
    """
    A classroom or laboratory.

    A room is AVAILABLE only when it is in service and completely empty.
    `occupied` is the head-count of the session currently using the room.
    """
    room_id: str
    name: str
    building_id: str
    room_type: str
    capacity: int
    in_service: bool = True
    occupied: int = 0
    has_projector: bool = False
    has_computers: bool = False
    temperature_c: float = 24.0
    energy_kwh: float = 0.0

    def __post_init__(self) -> None:
        self.room_id = self.room_id.strip().upper()
        self.building_id = self.building_id.strip().upper()
        self.room_type = self.room_type.strip().lower()
        if not self.room_id:
            raise ValueError("A room needs a non-empty ID.")
        if self.room_type not in ROOM_TYPES:
            raise ValueError(f"Room type must be one of {ROOM_TYPES}.")
        if self.capacity <= 0:
            raise ValueError("Room capacity must be at least 1.")
        if not 0 <= self.occupied <= self.capacity:
            raise ValueError("Occupancy must be between 0 and the room capacity.")

    @property
    def physically_free(self) -> bool:
        """In service and nobody inside (timetable is checked separately)."""
        return self.in_service and self.occupied == 0


@dataclass
class Booking:
    """
    A timetable entry for one room. Exactly one of `weekday` (repeats every
    week) or `date` (one-off) is set. Times are minutes after midnight and
    the interval is half-open: [start, end).
    """
    booking_id: int
    room_id: str
    title: str
    start: int
    end: int
    headcount: int
    weekday: Optional[int] = None
    date: Optional[dt.date] = None
    walk_in: bool = False

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("A booking needs a title.")
        if (self.weekday is None) == (self.date is None):
            raise ValueError("A booking must be either weekly or for one date.")
        if self.weekday is not None and not 0 <= self.weekday <= 6:
            raise ValueError("Weekday must be between Monday and Sunday.")
        if not 0 <= self.start < self.end <= MINUTES_PER_DAY:
            raise ValueError("A booking must start before it ends, within the same day.")
        if self.headcount < 1:
            raise ValueError("A booking needs at least 1 person.")

    @property
    def recurring(self) -> bool:
        return self.weekday is not None

    def applies_on(self, day: dt.date) -> bool:
        if self.recurring:
            return day.weekday() == self.weekday
        return day == self.date

    def clashes_with(self, other: "Booking") -> bool:
        """True if both use the same room at an overlapping time on some day."""
        if self.room_id != other.room_id:
            return False
        if not (self.start < other.end and other.start < self.end):
            return False
        if self.recurring and other.recurring:
            return self.weekday == other.weekday
        if self.recurring:
            return other.date.weekday() == self.weekday
        if other.recurring:
            return self.date.weekday() == other.weekday
        return self.date == other.date

    def when_text(self) -> str:
        if self.recurring:
            return f"every {DAY_NAMES[self.weekday]}"
        return f"{self.date.isoformat()} ({DAY_NAMES[self.date.weekday()]})"

    def summary(self) -> str:
        return (f"#{self.booking_id} {self.title} - {self.when_text()}, "
                f"{fmt_time(self.start)}-{fmt_time(self.end)}, {self.headcount} people")


@dataclass(frozen=True)
class TimeWindow:
    """A specific day and time range, used to ask 'is this room free then?'"""
    day: dt.date
    start: int
    end: int


@dataclass
class SensorReading:
    """Latest simulated sensor reading for a room."""
    sensor_id: str
    target_id: str
    temperature_c: float
    energy_kwh: float
    occupancy: int
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# 2. DISJOINT SET UNION
# ---------------------------------------------------------------------------

class DisjointSetUnion:
    """Union-Find with path compression and union by rank."""

    def __init__(self, items: Iterable[str]) -> None:
        self.parent: Dict[str, str] = {item: item for item in items}
        self.rank: Dict[str, int] = {item: 0 for item in self.parent}

    def find(self, item: str) -> str:
        if item not in self.parent:
            raise ValueError(f"Unknown item: {item}")
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != root:          # iterative path compression
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, a: str, b: str) -> bool:
        """Join two sets. Returns False if they were already joined."""
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return False
        if self.rank[root_a] < self.rank[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        if self.rank[root_a] == self.rank[root_b]:
            self.rank[root_a] += 1
        return True

    def connected(self, a: str, b: str) -> bool:
        return self.find(a) == self.find(b)

    def component_count(self) -> int:
        return len({self.find(item) for item in self.parent})


# ---------------------------------------------------------------------------
# 3. GRAPH (ADJACENCY LIST)
# ---------------------------------------------------------------------------

class CampusGraph:
    """
    Undirected weighted graph: vertices are locations, edges are walkable
    pathways, weights are walking distances in metres.
    """

    def __init__(self) -> None:
        self.locations: Dict[str, CampusLocation] = {}
        self.adj: Dict[str, List[Tuple[str, float]]] = {}
        # Blocked pathways (roads): edge -> reason. The buildings at both ends stay open.
        self.blocked_edges: Dict[frozenset, str] = {}
        # Closed buildings: location ID -> reason. They cannot be entered or crossed.
        self.closed_buildings: Dict[str, str] = {}

    # ----- building the graph -----

    def add_location(self, location: CampusLocation) -> None:
        self.locations[location.location_id] = location
        self.adj.setdefault(location.location_id, [])

    def add_path(self, a: str, b: str, distance: float) -> None:
        """Create/update a two-way pathway between two existing locations."""
        if a not in self.locations or b not in self.locations:
            raise ValueError("Both locations must exist before adding a pathway.")
        if a == b:
            raise ValueError("A pathway must connect two different locations.")
        if not math.isfinite(distance) or distance <= 0:
            raise ValueError("Pathway distance must be a positive number.")
        # A* needs edge length >= straight-line distance to stay correct.
        if distance + 1e-9 < self.straight_line_distance(a, b):
            raise ValueError(
                f"Pathway {a}-{b} ({distance} m) is shorter than the straight-line "
                f"distance ({self.straight_line_distance(a, b):.1f}); check the data."
            )
        self._upsert_neighbor(a, b, float(distance))
        self._upsert_neighbor(b, a, float(distance))

    def _upsert_neighbor(self, source: str, target: str, distance: float) -> None:
        for index, (neighbor, _) in enumerate(self.adj[source]):
            if neighbor == target:
                self.adj[source][index] = (target, distance)
                return
        self.adj[source].append((target, distance))

    # ----- path state (roads) -----

    def has_path(self, a: str, b: str) -> bool:
        return any(neighbor == b for neighbor, _ in self.adj.get(a, []))

    def is_blocked(self, a: str, b: str) -> bool:
        """True if THIS pathway (road) is blocked. Says nothing about the buildings."""
        return frozenset((a, b)) in self.blocked_edges

    def block_reason(self, a: str, b: str) -> str:
        return self.blocked_edges.get(frozenset((a, b)), "")

    def set_path_blocked(self, a: str, b: str, blocked: bool, reason: str = "") -> bool:
        """Block/unblock a pathway. Returns True if the state actually changed."""
        if not self.has_path(a, b):
            raise ValueError(f"No direct pathway exists between {a} and {b}.")
        edge = frozenset((a, b))
        if blocked and edge not in self.blocked_edges:
            self.blocked_edges[edge] = reason or "Other"
            return True
        if not blocked and edge in self.blocked_edges:
            del self.blocked_edges[edge]
            return True
        return False

    # ----- building state (closures) -----

    def is_closed(self, location_id: str) -> bool:
        """True if the whole building/location is closed (e.g. under construction)."""
        return location_id in self.closed_buildings

    def set_building_closed(self, location_id: str, closed: bool, reason: str = "") -> bool:
        """Close/reopen a whole building. Returns True if the state actually changed."""
        if location_id not in self.locations:
            raise ValueError(f"Unknown location: {location_id}")
        if closed and location_id not in self.closed_buildings:
            self.closed_buildings[location_id] = reason or "Other"
            return True
        if not closed and location_id in self.closed_buildings:
            del self.closed_buildings[location_id]
            return True
        return False

    def open_locations(self) -> List[str]:
        return [lid for lid in self.locations if lid not in self.closed_buildings]

    def neighbors(self, location_id: str) -> Iterable[Tuple[str, float]]:
        """Neighbours reachable through OPEN pathways into OPEN buildings only."""
        for neighbor, distance in self.adj.get(location_id, []):
            if self.is_blocked(location_id, neighbor) or self.is_closed(neighbor):
                continue
            yield neighbor, distance

    def straight_line_distance(self, a: str, b: str) -> float:
        pa, pb = self.locations[a], self.locations[b]
        return math.hypot(pa.x - pb.x, pa.y - pb.y)

    def _check_endpoints(self, start: str, goal: str) -> None:
        if start not in self.locations or goal not in self.locations:
            raise ValueError("Start and destination must be valid campus locations.")
        for place in (start, goal):
            if self.is_closed(place):
                raise ValueError(
                    f"{self.locations[place].name} ({place}) is CLOSED "
                    f"({self.closed_buildings[place]}), so it cannot be a start or destination."
                )

    @staticmethod
    def _rebuild_path(came_from: Dict[str, str], goal: str) -> List[str]:
        path = [goal]
        while path[-1] in came_from:
            path.append(came_from[path[-1]])
        path.reverse()
        return path

    # ----- route finding -----

    def a_star(self, start: str, goal: str) -> Tuple[Optional[List[str]], float]:
        """A* search. Returns (path, distance) or (None, inf) if unreachable."""
        self._check_endpoints(start, goal)
        if start == goal:
            return [start], 0.0

        heap: List[Tuple[float, float, str]] = [
            (self.straight_line_distance(start, goal), 0.0, start)
        ]
        came_from: Dict[str, str] = {}
        best_g: Dict[str, float] = {start: 0.0}

        while heap:
            _, g, current = heapq.heappop(heap)
            if g > best_g.get(current, math.inf):
                continue                                  # stale heap entry
            if current == goal:
                return self._rebuild_path(came_from, goal), g
            for neighbor, weight in self.neighbors(current):
                candidate = g + weight
                if candidate < best_g.get(neighbor, math.inf):
                    best_g[neighbor] = candidate
                    came_from[neighbor] = current
                    f = candidate + self.straight_line_distance(neighbor, goal)
                    heapq.heappush(heap, (f, candidate, neighbor))
        return None, math.inf

    def dijkstra_all(self, start: str) -> Tuple[Dict[str, float], Dict[str, str]]:
        """
        Dijkstra from ONE start to EVERY reachable location in a single run.
        Returns (distance to each reachable location, came_from map for rebuilding routes).
        Used when there is no single destination, e.g. 'which free room is nearest?'.
        """
        self._check_endpoints(start, start)
        distances: Dict[str, float] = {start: 0.0}
        came_from: Dict[str, str] = {}
        heap: List[Tuple[float, str]] = [(0.0, start)]

        while heap:
            dist, node = heapq.heappop(heap)
            if dist > distances.get(node, math.inf):
                continue
            for neighbor, weight in self.neighbors(node):
                candidate = dist + weight
                if candidate < distances.get(neighbor, math.inf):
                    distances[neighbor] = candidate
                    came_from[neighbor] = node
                    heapq.heappush(heap, (candidate, neighbor))
        return distances, came_from

    def route_from_map(self, came_from: Dict[str, str], goal: str) -> List[str]:
        """Rebuild the route to `goal` from a came_from map produced by dijkstra_all."""
        return self._rebuild_path(came_from, goal)

    # ----- network analysis -----

    def connectivity(self) -> DisjointSetUnion:
        """Which OPEN locations are linked by OPEN pathways (closed buildings are left out)."""
        dsu = DisjointSetUnion(self.open_locations())
        for source in list(dsu.parent):
            for target, _ in self.neighbors(source):
                dsu.union(source, target)
        return dsu

    def all_pathways(self) -> List[Tuple[str, str, float, str]]:
        """Every pathway once as (a, b, metres, status). Status is 'OPEN' or why it is unusable."""
        rows = []
        for source in sorted(self.adj):
            for target, distance in self.adj[source]:
                if source >= target:
                    continue
                if self.is_blocked(source, target):
                    status = f"BLOCKED - {self.block_reason(source, target)}"
                elif self.is_closed(source) or self.is_closed(target):
                    closed = source if self.is_closed(source) else target
                    status = f"UNUSABLE - {closed} is closed ({self.closed_buildings[closed]})"
                else:
                    status = "OPEN"
                rows.append((source, target, distance, status))
        return rows

    def minimum_spanning_tree(self) -> List[Tuple[str, str, float]]:
        """Kruskal MST over open pathways (a forest if the open network is split)."""
        edges = []
        for source in self.open_locations():
            for target, weight in self.neighbors(source):
                if source < target:                       # list each edge once
                    edges.append((weight, source, target))
        edges.sort()
        dsu = DisjointSetUnion(self.open_locations())
        return [(a, b, w) for w, a, b in edges if dsu.union(a, b)]


# ---------------------------------------------------------------------------
# 4. KD-TREE
# ---------------------------------------------------------------------------

@dataclass
class KDNode:
    point: Tuple[float, float, str]
    axis: int
    left: Optional["KDNode"] = None
    right: Optional["KDNode"] = None


class KDTree:
    """2D KD-tree for nearest-location lookup by coordinates."""

    def __init__(self, points: List[Tuple[float, float, str]]) -> None:
        self.root = self._build(list(points), 0)

    def _build(self, points: List[Tuple[float, float, str]], depth: int) -> Optional[KDNode]:
        if not points:
            return None
        axis = depth % 2
        points.sort(key=lambda p: p[axis])
        mid = len(points) // 2
        node = KDNode(points[mid], axis)
        node.left = self._build(points[:mid], depth + 1)
        node.right = self._build(points[mid + 1:], depth + 1)
        return node

    def nearest(self, x: float, y: float) -> Optional[Tuple[str, float]]:
        best: List[Optional[Tuple[float, str]]] = [None]

        def visit(node: Optional[KDNode]) -> None:
            if node is None:
                return
            px, py, location_id = node.point
            dist_sq = (x - px) ** 2 + (y - py) ** 2
            if best[0] is None or dist_sq < best[0][0]:
                best[0] = (dist_sq, location_id)
            delta = (x - px) if node.axis == 0 else (y - py)
            near, far = (node.left, node.right) if delta < 0 else (node.right, node.left)
            visit(near)
            if best[0] is None or delta * delta <= best[0][0]:
                visit(far)

        visit(self.root)
        if best[0] is None:
            return None
        return best[0][1], math.sqrt(best[0][0])


# ---------------------------------------------------------------------------
# 5. FENWICK TREE
# ---------------------------------------------------------------------------

class FenwickTree:
    """Point update and prefix/range sums in O(log n)."""

    def __init__(self, values: List[float]) -> None:
        self.n = len(values)
        self.tree = [0.0] * (self.n + 1)
        self.values = [0.0] * self.n          # exact copy, avoids rounding drift
        for index, value in enumerate(values, start=1):
            self.add(index, value)

    def _check(self, index: int) -> None:
        if index < 1 or index > self.n:
            raise IndexError(f"Position must be between 1 and {self.n}.")

    def add(self, index: int, delta: float) -> None:
        self._check(index)
        self.values[index - 1] += delta
        while index <= self.n:
            self.tree[index] += delta
            index += index & -index

    def set_value(self, index: int, new_value: float) -> None:
        self._check(index)
        self.add(index, new_value - self.values[index - 1])

    def prefix_sum(self, index: int) -> float:
        if index < 0 or index > self.n:
            raise IndexError(f"Position must be between 0 and {self.n}.")
        total = 0.0
        while index > 0:
            total += self.tree[index]
            index -= index & -index
        return total

    def range_sum(self, left: int, right: int) -> float:
        if left < 1 or right > self.n or left > right:
            raise IndexError(f"Range must satisfy 1 <= start <= end <= {self.n}.")
        return self.prefix_sum(right) - self.prefix_sum(left - 1)


# ---------------------------------------------------------------------------
# 6. PRIORITY QUEUE FOR ALERTS
# ---------------------------------------------------------------------------

class AlertQueue:
    """Min-heap: priority 1 is most urgent. Duplicate pending alerts are ignored."""

    def __init__(self) -> None:
        self._heap: List[Tuple[int, int, str]] = []
        self._pending: Set[str] = set()
        self._counter = 0

    def add_alert(self, priority: int, message: str) -> bool:
        if message in self._pending:
            return False
        self._counter += 1
        self._pending.add(message)
        heapq.heappush(self._heap, (priority, self._counter, message))
        return True

    def pop_alert(self) -> Optional[Tuple[int, str]]:
        if not self._heap:
            return None
        priority, _, message = heapq.heappop(self._heap)
        self._pending.discard(message)
        return priority, message

    def show_alerts(self) -> List[Tuple[int, str]]:
        return [(p, msg) for p, _, msg in sorted(self._heap)]


# ---------------------------------------------------------------------------
# 7. TEXT SEARCH
# ---------------------------------------------------------------------------

def kmp_search(text: str, pattern: str) -> List[int]:
    """Knuth-Morris-Pratt: start index of every occurrence of pattern."""
    if pattern == "":
        return list(range(len(text) + 1))
    lps = [0] * len(pattern)
    length, i = 0, 1
    while i < len(pattern):
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        elif length:
            length = lps[length - 1]
        else:
            i += 1

    matches: List[int] = []
    i = j = 0
    while i < len(text):
        if text[i] == pattern[j]:
            i += 1
            j += 1
            if j == len(pattern):
                matches.append(i - j)
                j = lps[j - 1]
        elif j:
            j = lps[j - 1]
        else:
            i += 1
    return matches


# ---------------------------------------------------------------------------
# 8. THE APPLICATION
# ---------------------------------------------------------------------------

class SmartCampus:
    """Ties all data structures together and exposes campus operations."""

    def __init__(self) -> None:
        self.graph = CampusGraph()
        self.rooms: Dict[str, Room] = {}
        self.sensors: Dict[str, SensorReading] = {}
        self.alerts = AlertQueue()
        self.building_energy: Dict[str, float] = {}
        self.energy_building_order: List[str] = []
        self.energy_tree = FenwickTree([])
        self.kd_tree = KDTree([])
        self.bookings: Dict[int, Booking] = {}
        self._next_booking_id = 1
        self._walkins: Dict[str, int] = {}          # room ID -> walk-in booking ID
        self._fixed_now: Optional[dt.datetime] = None
        self._load_sample_campus()

    # ----- clock -----

    def now(self) -> dt.datetime:
        """Current time: the real clock, or a frozen simulated time."""
        return self._fixed_now or dt.datetime.now()

    @property
    def clock_is_simulated(self) -> bool:
        return self._fixed_now is not None

    def _now_minutes(self) -> int:
        current = self.now()
        return current.hour * 60 + current.minute

    def set_clock(self, when: Optional[dt.datetime]) -> None:
        """Freeze the clock at `when`, or pass None to use the real clock."""
        self._fixed_now = when
        for room in self.rooms.values():
            self._flag_unscheduled(room)

    # ----- setup -----

    def _load_sample_campus(self) -> None:
        for loc in [
            CampusLocation("GATE", "Main Gate", 0, 0, "gate"),
            CampusLocation("LIB", "Central Library", 20, 10),
            CampusLocation("CSE", "Computer Science Block", 45, 12),
            CampusLocation("LAB", "Innovation Laboratory", 55, 35),
            CampusLocation("SCI", "Science Block", 25, 42),
            CampusLocation("CAF", "Cafeteria", 5, 35),
            CampusLocation("AUD", "Auditorium", 70, 10),
            CampusLocation("HOST", "Hostel", 85, 38),
        ]:
            self.graph.add_location(loc)

        for a, b, distance in [
            ("GATE", "LIB", 23), ("GATE", "CAF", 36),
            ("LIB", "CSE", 26), ("LIB", "SCI", 34),
            ("CAF", "SCI", 25), ("SCI", "LAB", 34),
            ("CSE", "LAB", 28), ("CSE", "AUD", 26),
            ("LAB", "HOST", 32), ("AUD", "HOST", 39),
            ("AUD", "LAB", 30),
        ]:
            self.graph.add_path(a, b, distance)

        for room in [
            Room("CSE101", "CSE Classroom 101", "CSE", "classroom", 60,
                 has_projector=True, temperature_c=23.5, energy_kwh=12.4),
            Room("CSE102", "CSE Classroom 102", "CSE", "classroom", 40,
                 has_projector=True, temperature_c=24.0, energy_kwh=9.8),
            Room("CSELAB1", "Programming Lab 1", "CSE", "laboratory", 35,
                 has_projector=True, has_computers=True,
                 temperature_c=22.8, energy_kwh=21.2),
            Room("INNO1", "Innovation Lab 1", "LAB", "laboratory", 28,
                 has_projector=True, has_computers=True,
                 temperature_c=23.2, energy_kwh=18.5),
            Room("SCI201", "Science Classroom 201", "SCI", "classroom", 50,
                 temperature_c=26.5, energy_kwh=14.3),
            Room("SCI-LAB", "Science Lab", "SCI", "laboratory", 24,
                 in_service=False, has_computers=True,
                 temperature_c=24.5, energy_kwh=16.8),
            Room("AUD1", "Seminar Room", "AUD", "classroom", 80,
                 has_projector=True, has_computers=True,
                 temperature_c=22.0, energy_kwh=25.1),
        ]:
            self.add_room(room)

        # Sample weekly timetable: (room, title, start h, start m, end h, end m, people, weekdays)
        # weekdays: 0 = Monday ... 4 = Friday
        for room_id, title, sh, sm, eh, em, people, weekdays in [
            ("CSE101", "Data Structures", 9, 0, 10, 0, 42, [0, 2, 4]),
            ("CSE101", "Algorithms", 11, 0, 12, 30, 40, [1, 3]),
            ("CSE102", "Mathematics", 10, 0, 11, 0, 35, [0, 1, 2, 3, 4]),
            ("CSELAB1", "Programming Lab", 14, 0, 17, 0, 30, [0, 2]),
            ("CSELAB1", "Database Lab", 9, 0, 12, 0, 28, [1, 3]),
            ("INNO1", "Innovation Workshop", 10, 0, 13, 0, 20, [3]),
            ("SCI201", "Physics", 9, 0, 12, 0, 50, [0, 1, 2, 3, 4]),
            ("AUD1", "Guest Seminar", 15, 0, 17, 0, 70, [4]),
        ]:
            self.add_weekly_bookings(room_id, title, sh * 60 + sm, eh * 60 + em, people, weekdays)

        self.building_energy = {
            "CSE": 124.5, "LIB": 80.2, "LAB": 112.8, "SCI": 97.1, "AUD": 75.4
        }
        self._rebuild_energy_tree()
        self.rebuild_kd_tree()

    def add_room(self, room: Room) -> None:
        if room.building_id not in self.graph.locations:
            raise ValueError(f"Building {room.building_id} does not exist.")
        if room.room_id in self.rooms:
            raise ValueError(f"Room {room.room_id} already exists.")
        self.rooms[room.room_id] = room
        self._sync_sensor(room)

    def _rebuild_energy_tree(self) -> None:
        self.energy_building_order = list(self.building_energy)
        self.energy_tree = FenwickTree(
            [self.building_energy[b] for b in self.energy_building_order]
        )

    def rebuild_kd_tree(self) -> None:
        self.kd_tree = KDTree(
            [(loc.x, loc.y, loc.location_id) for loc in self.graph.locations.values()]
        )

    # ----- timetable -----

    def add_booking(
        self,
        room_id: str,
        title: str,
        start: int,
        end: int,
        headcount: int,
        weekday: Optional[int] = None,
        day: Optional[dt.date] = None,
        walk_in: bool = False,
    ) -> Booking:
        """Add one booking after checking room state, capacity, date and clashes."""
        room = self.get_room(room_id)
        if not room.in_service:
            raise ValueError(f"{room.room_id} is out of service and cannot be booked.")
        if self.graph.is_closed(room.building_id):
            raise ValueError(
                f"{room.room_id} cannot be booked: building {room.building_id} is closed "
                f"({self.graph.closed_buildings[room.building_id]})."
            )
        if headcount > room.capacity:
            raise ValueError(f"{room.room_id} holds only {room.capacity} people.")
        booking = Booking(self._next_booking_id, room.room_id, title, start, end,
                          headcount, weekday, day, walk_in)
        if day is not None:
            today = self.now().date()
            if day < today:
                raise ValueError("Cannot book a date in the past.")
            if day == today and end <= self._now_minutes():
                raise ValueError("That time has already passed today.")
        for other in self.bookings.values():
            if booking.clashes_with(other):
                raise ValueError(
                    f"{room.room_id} is already booked then: {other.summary()}."
                )
        self.bookings[booking.booking_id] = booking
        self._next_booking_id += 1
        return booking

    def add_weekly_bookings(
        self, room_id: str, title: str, start: int, end: int,
        headcount: int, weekdays: Iterable[int],
    ) -> List[Booking]:
        """Add the same weekly slot on several weekdays - all or nothing."""
        created: List[Booking] = []
        try:
            for weekday in sorted(set(weekdays)):
                created.append(self.add_booking(room_id, title, start, end, headcount, weekday=weekday))
        except ValueError:
            for booking in created:
                del self.bookings[booking.booking_id]
            raise
        if not created:
            raise ValueError("Choose at least one weekday.")
        return created

    def cancel_booking(self, booking_id: int) -> Booking:
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise ValueError(f"No booking with ID {booking_id}.")
        if booking.walk_in:
            raise ValueError("Walk-in sessions end with 'End session' in the room-control menu.")
        del self.bookings[booking_id]
        return booking

    def bookings_on(self, room_id: str, day: dt.date) -> List[Booking]:
        found = [b for b in self.bookings.values()
                 if b.room_id == room_id and b.applies_on(day)]
        return sorted(found, key=lambda b: b.start)

    def active_booking(self, room_id: str) -> Optional[Booking]:
        """The booking running in this room right now, if any."""
        minute = self._now_minutes()
        for booking in self.bookings_on(room_id, self.now().date()):
            if booking.start <= minute < booking.end:
                return booking
        return None

    def next_booking_today(self, room_id: str) -> Optional[Booking]:
        minute = self._now_minutes()
        for booking in self.bookings_on(room_id, self.now().date()):
            if booking.start > minute:
                return booking
        return None

    def make_window(self, day: dt.date, start: int, end: int) -> TimeWindow:
        """Validate a time window (must not lie in the past)."""
        if not 0 <= start < end <= MINUTES_PER_DAY:
            raise ValueError("The end time must be after the start time, within one day.")
        today = self.now().date()
        if day < today or (day == today and end <= self._now_minutes()):
            raise ValueError("That time window is already over.")
        return TimeWindow(day, start, end)

    # ----- availability -----

    def building_closed(self, room: Room) -> bool:
        """True if the building that contains this room is closed."""
        return self.graph.is_closed(room.building_id)

    def is_available_now(self, room: Room) -> bool:
        """Free right now: building open, room in service, empty, and no booked class running."""
        return (not self.building_closed(room)
                and room.physically_free
                and self.active_booking(room.room_id) is None)

    def is_free_during(self, room: Room, window: TimeWindow) -> bool:
        """Free for the whole window: building open, room in service, no booking overlaps it."""
        if self.building_closed(room) or not room.in_service:
            return False
        for booking in self.bookings_on(room.room_id, window.day):
            if booking.start < window.end and window.start < booking.end:
                return False
        today = self.now().date()
        if window.day == today and window.start <= self._now_minutes() < window.end:
            if room.occupied > 0:                 # people are inside right now
                return False
        return True

    def room_counts(self) -> Tuple[int, int, int]:
        """(free now, busy or reserved, unavailable = out of service or building closed)."""
        rooms = list(self.rooms.values())
        free = sum(1 for r in rooms if self.is_available_now(r))
        unavailable = sum(1 for r in rooms if not r.in_service or self.building_closed(r))
        return free, len(rooms) - free - unavailable, unavailable

    def status_text(self, room: Room) -> str:
        """One-line status such as 'FREE until 14:00' or 'RESERVED - Physics until 12:00'."""
        if self.building_closed(room):
            return f"BUILDING CLOSED - {self.graph.closed_buildings[room.building_id]}"
        if not room.in_service:
            return "OUT OF SERVICE"
        active = self.active_booking(room.room_id)
        if room.occupied > 0:
            people = f"{room.occupied} people inside"
            if active:
                return f"IN USE - {active.title} until {fmt_time(active.end)} ({people})"
            return f"IN USE - not booked ({people})"
        if active:
            return f"RESERVED - {active.title} until {fmt_time(active.end)}"
        upcoming = self.next_booking_today(room.room_id)
        if upcoming:
            return f"FREE until {fmt_time(upcoming.start)}"
        return "FREE for the rest of the day"

    # ----- room lookup and search -----

    def get_room(self, room_id: str) -> Room:
        key = room_id.strip().upper()
        if key not in self.rooms:
            raise ValueError(f"Unknown room ID: {room_id.strip() or '(blank)'}")
        return self.rooms[key]

    def find_rooms(
        self,
        room_type: Optional[str] = None,
        min_capacity: int = 0,
        projector: Optional[bool] = None,
        computers: Optional[bool] = None,
        available_only: bool = True,
        window: Optional[TimeWindow] = None,
        keyword: Optional[str] = None,
    ) -> List[Room]:
        """
        Filter rooms.
          * projector / computers: True = MUST have, False = must NOT have,
            None = don't care.
          * keyword: text searched (KMP) in the room ID, room name and building name.
          * available_only: window=None means 'free right now'; otherwise the
            room must be free for the whole window.
        Smallest fit first.
        """
        needle = (keyword or "").strip().lower()
        results = []
        for room in self.rooms.values():
            if room_type and room.room_type != room_type.lower():
                continue
            if room.capacity < min_capacity:
                continue
            if projector is not None and room.has_projector != projector:
                continue
            if computers is not None and room.has_computers != computers:
                continue
            if needle:
                building = self.graph.locations[room.building_id].name
                haystack = f"{room.room_id} {room.name} {building}".lower()
                if not kmp_search(haystack, needle):
                    continue
            if available_only:
                free = self.is_available_now(room) if window is None else self.is_free_during(room, window)
                if not free:
                    continue
            results.append(room)
        return sorted(results, key=lambda r: (r.capacity, r.room_id))

    def nearest_available_room(
        self,
        origin_id: str,
        room_type: Optional[str] = None,
        min_capacity: int = 0,
        projector: Optional[bool] = None,
        computers: Optional[bool] = None,
        window: Optional[TimeWindow] = None,
    ) -> Tuple[int, List[Tuple[Room, List[str], float]]]:
        """
        Returns (number of matching free rooms, reachable rooms ranked by
        real walking distance). Blocked pathways and closed buildings are respected.

        Dijkstra is used here because there is no single goal: ONE run from the
        start finds the distance to EVERY building, which is then used to rank
        all the free rooms (A* is better for a single start-to-destination route).
        """
        if origin_id not in self.graph.locations:
            raise ValueError("Unknown starting location.")
        distances, came_from = self.graph.dijkstra_all(origin_id)
        eligible = self.find_rooms(room_type, min_capacity, projector, computers, True, window)
        ranked = []
        for room in eligible:
            if room.building_id in distances:
                path = self.graph.route_from_map(came_from, room.building_id)
                ranked.append((room, path, distances[room.building_id]))
        ranked.sort(key=lambda item: (item[2], item[0].room_id))
        return len(eligible), ranked

    # ----- live room usage -----

    def start_session(self, room_id: str, headcount: int, duration: Optional[int] = None) -> Optional[Booking]:
        """
        People enter the room.
        * If a booked class is running, this records that class arriving.
        * Otherwise it is a walk-in: it needs a duration in minutes and is
          booked automatically, so it cannot run into the next scheduled class.
        The room must be in service and completely empty.
        """
        room = self.get_room(room_id)
        if self.graph.is_closed(room.building_id):
            raise ValueError(
                f"Building {room.building_id} is closed "
                f"({self.graph.closed_buildings[room.building_id]}); {room.room_id} cannot be used."
            )
        if not room.in_service:
            raise ValueError(f"{room.room_id} is out of service and cannot be used.")
        if room.occupied > 0:
            raise ValueError(
                f"{room.room_id} is in use ({room.occupied} people). "
                "A room can only be entered when it is completely free."
            )
        if headcount < 1 or headcount > room.capacity:
            raise ValueError(f"Head-count must be between 1 and {room.capacity}.")

        walk_in: Optional[Booking] = None
        if self.active_booking(room.room_id) is None:
            if duration is None or duration < 1:
                raise ValueError("A walk-in session needs a duration in minutes.")
            start = self._now_minutes()
            if start + duration > MINUTES_PER_DAY:
                raise ValueError("A session cannot run past midnight; choose a shorter duration.")
            walk_in = self.add_booking(room.room_id, "Walk-in session", start, start + duration,
                                       headcount, day=self.now().date(), walk_in=True)
            self._walkins[room.room_id] = walk_in.booking_id
        room.occupied = headcount
        self._sync_sensor(room)
        if headcount == room.capacity:
            self.alerts.add_alert(3, f"Room {room.room_id} is at full capacity.")
        return walk_in

    def end_session(self, room_id: str) -> str:
        """Everyone leaves. A walk-in booking is shortened so the room frees up."""
        room = self.get_room(room_id)
        if room.occupied == 0:
            raise ValueError(f"{room.room_id} has no session running.")
        room.occupied = 0
        self._sync_sensor(room)

        booking = self.bookings.get(self._walkins.pop(room.room_id, -1))
        if booking is not None and booking.applies_on(self.now().date()):
            minute = self._now_minutes()
            if booking.start <= minute < booking.end:
                if minute <= booking.start:
                    del self.bookings[booking.booking_id]
                else:
                    booking.end = minute
        return self.status_text(room)

    def adjust_headcount(self, room_id: str, headcount: int) -> None:
        """Correct the head-count of a session that is already running."""
        room = self.get_room(room_id)
        if room.occupied == 0:
            raise ValueError(f"{room.room_id} is free; start a session instead.")
        if headcount == 0:
            self.end_session(room_id)
            return
        if headcount < 1 or headcount > room.capacity:
            raise ValueError(f"Head-count must be between 0 and {room.capacity}.")
        room.occupied = headcount
        self._sync_sensor(room)
        if headcount == room.capacity:
            self.alerts.add_alert(3, f"Room {room.room_id} is at full capacity.")
        self._flag_unscheduled(room)

    def set_in_service(self, room_id: str, in_service: bool) -> bool:
        """Maintenance switch. Returns True if the state changed."""
        room = self.get_room(room_id)
        if room.in_service == in_service:
            return False
        room.in_service = in_service
        if not in_service:
            self.alerts.add_alert(2, f"{room.room_id} taken out of service.")
            if room.occupied > 0:
                self.alerts.add_alert(
                    1, f"{room.room_id} is out of service but {room.occupied} people are inside."
                )
            today = self.now().date()
            pending = [b for b in self.bookings.values()
                       if b.room_id == room.room_id and not b.walk_in
                       and (b.recurring or b.date >= today)]
            if pending:
                self.alerts.add_alert(
                    2, f"{room.room_id} is out of service but has {len(pending)} booking(s) "
                       "in its timetable - rebook them elsewhere."
                )
        else:
            self.alerts.add_alert(4, f"{room.room_id} is back in service.")
        return True

    def _flag_unscheduled(self, room: Room) -> None:
        """Alert when people are inside a room that has no booking right now."""
        if room.occupied > 0 and self.active_booking(room.room_id) is None:
            self.alerts.add_alert(2, f"{room.room_id} has people inside but no booking is active.")

    def _sync_sensor(self, room: Room) -> None:
        sensor_id = f"S-{room.room_id}"
        self.sensors[sensor_id] = SensorReading(
            sensor_id, room.room_id, room.temperature_c, room.energy_kwh, room.occupied
        )

    def simulate_sensor_update(self, room_id: str) -> SensorReading:
        """Generate plausible random readings (demo only)."""
        room = self.get_room(room_id)
        room.temperature_c = round(random.uniform(21.0, 29.0), 1)
        room.energy_kwh = round(room.energy_kwh + random.uniform(0.1, 2.0), 2)
        room.occupied = 0 if not room.in_service else random.randint(0, room.capacity)
        self._sync_sensor(room)
        if room.temperature_c >= HIGH_TEMPERATURE_C:
            self.alerts.add_alert(1, f"High temperature in {room.room_id}: {room.temperature_c} C")
        if room.occupied == room.capacity:
            self.alerts.add_alert(3, f"Room {room.room_id} is at full capacity.")
        self._flag_unscheduled(room)
        return self.sensors[f"S-{room.room_id}"]

    # ----- energy -----

    def update_building_energy(self, building_id: str, new_kwh: float) -> None:
        building_id = building_id.strip().upper()
        if building_id not in self.graph.locations:
            raise ValueError(f"{building_id} is not a campus location.")
        if not math.isfinite(new_kwh) or new_kwh < 0:
            raise ValueError("Energy consumption must be a non-negative number.")
        if building_id in self.building_energy:
            index = self.energy_building_order.index(building_id) + 1
            self.building_energy[building_id] = float(new_kwh)
            self.energy_tree.set_value(index, float(new_kwh))
        else:
            self.building_energy[building_id] = float(new_kwh)
            self._rebuild_energy_tree()

    def total_energy(self) -> float:
        return self.energy_tree.prefix_sum(self.energy_tree.n)

    def energy_between_positions(self, left: int, right: int) -> float:
        return self.energy_tree.range_sum(left, right)

    # ----- pathways and building closures -----

    def change_path_state(self, a: str, b: str, blocked: bool, reason: str = "") -> str:
        """Block/reopen ONE pathway (road) between two locations."""
        before = self.graph.connectivity().component_count()
        if not self.graph.set_path_blocked(a, b, blocked, reason):
            return f"Pathway {a} <-> {b} was already {'blocked' if blocked else 'open'}; no change."
        if blocked:
            reason = self.graph.block_reason(a, b)
            self.alerts.add_alert(2, f"Pathway blocked ({reason}): {a} <-> {b}")
            message = f"Pathway {a} <-> {b} is now BLOCKED ({reason})."
            if self.graph.connectivity().component_count() > before:
                self.alerts.add_alert(1, f"Campus split into separate parts by blocking {a} <-> {b}")
                message += "\nWarning: this blocks the only link between parts of the campus."
            return message
        self.alerts.add_alert(4, f"Pathway reopened: {a} <-> {b}")
        return f"Pathway {a} <-> {b} is now OPEN."

    def change_building_state(self, location_id: str, closed: bool, reason: str = "") -> str:
        """Close/reopen a WHOLE building (e.g. under construction)."""
        location_id = location_id.strip().upper()
        if location_id not in self.graph.locations:
            raise ValueError(f"{location_id} is not a campus location.")
        name = self.graph.locations[location_id].name
        before = self.graph.connectivity().component_count()
        if not self.graph.set_building_closed(location_id, closed, reason):
            return f"{name} ({location_id}) was already {'closed' if closed else 'open'}; no change."
        if not closed:
            self.alerts.add_alert(4, f"Building reopened: {name} ({location_id})")
            return (f"{name} ({location_id}) is now OPEN again. "
                    "Its rooms can be used and routes can pass through it.")

        reason = self.graph.closed_buildings[location_id]
        self.alerts.add_alert(2, f"Building closed ({reason}): {name} ({location_id})")
        lines = [f"{name} ({location_id}) is now CLOSED ({reason}).",
                 "Routes cannot enter or pass through it, and its rooms are unavailable."]
        rooms = [r for r in self.rooms.values() if r.building_id == location_id]
        inside = [r for r in rooms if r.occupied > 0]
        for room in inside:
            self.alerts.add_alert(
                1, f"{room.room_id} is in CLOSED building {location_id} but {room.occupied} people are inside."
            )
        if inside:
            lines.append("Warning: people are still inside " + ", ".join(r.room_id for r in inside) + ".")
        room_ids = {r.room_id for r in rooms}
        today = self.now().date()
        affected = [b for b in self.bookings.values()
                    if b.room_id in room_ids and not b.walk_in and (b.recurring or b.date >= today)]
        if affected:
            self.alerts.add_alert(
                2, f"{len(affected)} timetable booking(s) in closed building {location_id} - rebook them elsewhere."
            )
            lines.append(f"Warning: {len(affected)} timetable booking(s) in this building need a new room.")
        if self.graph.connectivity().component_count() > before:
            self.alerts.add_alert(1, f"Campus split into separate parts by closing {name} ({location_id})")
            lines.append("Warning: closing this building cuts off part of the campus.")
        return "\n".join(lines)

    def check_connectivity(self, a: str, b: str) -> bool:
        graph = self.graph
        return (not graph.is_closed(a) and not graph.is_closed(b)
                and graph.connectivity().connected(a, b))

    def describe_connection(self, a: str, b: str) -> List[str]:
        """Explain, line by line, how (and whether) two locations are connected."""
        graph = self.graph

        def label(x: str) -> str:
            return f"{graph.locations[x].name} ({x})"

        if a == b:
            return [f"{label(a)}: this is the same location, so there is nothing to connect."]

        lines: List[str] = []
        closed = [x for x in (a, b) if graph.is_closed(x)]
        if closed:
            for x in closed:
                lines.append(f"{label(x)} is CLOSED ({graph.closed_buildings[x]}): "
                             "nobody can reach it or walk through it.")
            lines.append("RESULT: NOT CONNECTED (a building is closed).")
            return lines

        direct_exists = graph.has_path(a, b)
        direct_open = direct_exists and not graph.is_blocked(a, b)
        if not direct_exists:
            lines.append("There is no direct pathway between these two locations.")
        elif not direct_open:
            lines.append(f"A direct pathway exists but it is BLOCKED ({graph.block_reason(a, b)}).")

        path, distance = graph.a_star(a, b)
        if path is None:
            lines.append("RESULT: NOT CONNECTED - no open route exists between them.")
            dsu = graph.connectivity()
            for x in (a, b):
                reachable = [lid for lid in graph.open_locations() if dsu.connected(lid, x)]
                lines.append(f"  From {x} you can still reach: {', '.join(reachable)}")
            lines.append("They are in separate parts of the campus "
                         "(blocked pathways or closed buildings cut the link).")
            return lines

        if len(path) == 2:
            lines.append(f"RESULT: DIRECTLY CONNECTED - one open pathway, {distance:.1f} m.")
        else:
            lines.append(f"RESULT: INDIRECTLY CONNECTED - you walk through {len(path) - 2} "
                         "other location(s).")
            lines.append("  Route: " + " -> ".join(path) + f"   ({distance:.1f} m)")
            if direct_exists and not direct_open:
                lines.append("  People have to go around the blocked pathway.")
        return lines

    # ----- reports -----

    def time_text(self) -> str:
        label = "SIMULATED - frozen" if self.clock_is_simulated else "real clock"
        return f"{self.now().strftime('%A %d %b %Y, %H:%M')} ({label})"

    def campus_summary(self) -> None:
        free, busy, unavailable = self.room_counts()
        print("\n" + "=" * 72)
        print("SMART CAMPUS DIGITAL TWIN - CAMPUS SUMMARY")
        print("=" * 72)
        print(f"Time now         : {self.time_text()}")
        print(f"Campus locations : {len(self.graph.locations)}")
        print(f"Rooms/labs       : {len(self.rooms)}  (free now: {free}, busy/reserved: {busy}, "
              f"unavailable: {unavailable})")
        print("                   (unavailable = out of service or its building is closed)")
        print(f"Timetable entries: {len(self.bookings)}")
        print(f"Sensor records   : {len(self.sensors)}")
        print(f"Blocked pathways : {len(self.graph.blocked_edges)}")
        print(f"Closed buildings : {len(self.graph.closed_buildings)}")
        print(f"Total energy     : {self.total_energy():.2f} kWh")
        print("\nLocations (ID | name | map position x, y | status):")
        for loc in self.graph.locations.values():
            closed = self.graph.closed_buildings.get(loc.location_id)
            state = f"CLOSED - {closed}" if closed else "open"
            print(f"  {loc.location_id:6} | {loc.name:24} | ({loc.x:5.1f}, {loc.y:5.1f}) | {state}")
        print("=" * 72)

    def list_rooms(self) -> None:
        line = "-" * 118
        print(f"\nROOMS AND LABORATORIES - {self.time_text()}")
        print(line)
        print(f"{'ID':9} {'Name':22} {'Bldg':5} {'Type':11} {'Cap.':>4} "
              f"{'Proj.':>5} {'PCs':>4} {'Available':>9}  Status")
        print(line)
        for room in self.rooms.values():
            print(f"{room.room_id:9} {room.name[:22]:22} {room.building_id:5} "
                  f"{room.room_type:11} {room.capacity:4} "
                  f"{yes_no_text(room.has_projector):>5} {yes_no_text(room.has_computers):>4} "
                  f"{yes_no_text(self.is_available_now(room)):>9}  {self.status_text(room)}")
        print(line)
        print("Proj. = has a projector, PCs = has computers.")
        print("Available = Yes only when the building is open, the room is in service, "
              "empty, and has no booked class right now.")

    def print_room_timetable(self, room_id: str) -> None:
        room = self.get_room(room_id)
        today = self.now().date()
        mine = [b for b in self.bookings.values() if b.room_id == room.room_id]
        weekly = sorted((b for b in mine if b.recurring), key=lambda b: (b.weekday, b.start))
        one_off = sorted((b for b in mine if not b.recurring and b.date >= today),
                         key=lambda b: (b.date, b.start))
        print(f"\nTIMETABLE - {room.room_id} ({room.name}), capacity {room.capacity}")
        print(f"Status now: {self.status_text(room)}")
        if not weekly and not one_off:
            print("No bookings: the room is free all day, every day.")
            return
        if weekly:
            print("Weekly (repeats every week):")
            for b in weekly:
                print(f"  {DAY_NAMES[b.weekday]:9} {fmt_time(b.start)}-{fmt_time(b.end)}  "
                      f"{b.title} ({b.headcount} people)  [#{b.booking_id}]")
        if one_off:
            print("One-off / upcoming:")
            for b in one_off:
                tag = "  (walk-in)" if b.walk_in else ""
                print(f"  {b.date.isoformat()} {DAY_NAMES[b.date.weekday()][:3]}  "
                      f"{fmt_time(b.start)}-{fmt_time(b.end)}  {b.title} "
                      f"({b.headcount} people)  [#{b.booking_id}]{tag}")

    def print_day_schedule(self, day: dt.date) -> None:
        print(f"\nSCHEDULE FOR {DAY_NAMES[day.weekday()]} {day.strftime('%d %b %Y')}")
        free_all_day = []
        for room in self.rooms.values():
            entries = self.bookings_on(room.room_id, day)
            if not entries:
                free_all_day.append(room.room_id)
                continue
            note = "  (out of service)" if not room.in_service else ""
            print(f"{room.room_id} - {room.name}{note}")
            for b in entries:
                print(f"   {fmt_time(b.start)}-{fmt_time(b.end)}  {b.title} "
                      f"({b.headcount} people)  [#{b.booking_id}]")
        if free_all_day:
            print("No bookings: " + ", ".join(free_all_day))

    def sensor_report(self) -> None:
        print("\nLATEST SIMULATED SENSOR READINGS")
        print("-" * 70)
        print(f"{'Sensor':12} {'Room':9} {'Temp (C)':>9} {'Energy kWh':>11} {'People':>7}  Updated")
        print("-" * 70)
        for r in self.sensors.values():
            stamp = time.strftime("%H:%M:%S", time.localtime(r.timestamp))
            people = str(r.occupancy) if r.occupancy else "-"
            print(f"{r.sensor_id:12} {r.target_id:9} {r.temperature_c:9.1f} "
                  f"{r.energy_kwh:11.2f} {people:>7}  {stamp}")
        print("People '-' means the room is empty.")

    def show_alerts(self) -> None:
        alerts = self.alerts.show_alerts()
        print("\nCAMPUS ALERTS - most urgent first")
        if not alerts:
            print("No pending alerts. Everything is under control.")
            return
        for number, (priority, message) in enumerate(alerts, start=1):
            level = ALERT_LEVELS.get(priority, f"P{priority}")
            print(f"  {number}. [{level}] {message}")
        print(f"{len(alerts)} alert(s) waiting.")

    def process_next_alert(self) -> None:
        alert = self.alerts.pop_alert()
        if alert is None:
            print("No alerts to handle.")
        else:
            level = ALERT_LEVELS.get(alert[0], f"P{alert[0]}")
            print(f"Marked as handled and removed: [{level}] {alert[1]}")


# ---------------------------------------------------------------------------
# 9. INPUT HELPERS
# ---------------------------------------------------------------------------

def read_int(prompt: str, minimum: Optional[int] = None, maximum: Optional[int] = None,
             default: Optional[int] = None) -> int:
    """Ask for a whole number. If a default is given, pressing Enter uses it."""
    while True:
        text = input(prompt).strip()
        if text == "" and default is not None:
            return default
        try:
            value = int(text)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Please enter a value of at least {minimum}.")
        elif maximum is not None and value > maximum:
            print(f"Please enter a value of at most {maximum}.")
        else:
            return value


def read_float(prompt: str, minimum: Optional[float] = None) -> float:
    while True:
        try:
            value = float(input(prompt).strip())
        except ValueError:
            print("Please enter a valid number.")
            continue
        if not math.isfinite(value):
            print("Please enter a finite number (not NaN or infinity).")
        elif minimum is not None and value < minimum:
            print(f"Please enter a value of at least {minimum}.")
        else:
            return value


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt + " (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter y or n.")


def read_time(prompt: str, allow_24: bool = False) -> int:
    """Ask until a valid time such as 14:30, 2:30pm or 9am is typed."""
    while True:
        minutes = parse_time(input(prompt).strip(), allow_24)
        if minutes is not None:
            return minutes
        print("Please enter a time like 14:30, 9:05 or 2:30pm.")


def read_day(app: SmartCampus, prompt: str) -> dt.date:
    """Ask until a valid day is typed. Blank means today."""
    today = app.now().date()
    while True:
        text = input(prompt).strip()
        if not text:
            return today
        day = parse_day(text, today)
        if day is not None:
            return day
        print("Use today, tomorrow, a weekday name (e.g. mon) or a date like 2026-10-26 or 26-10-2026.")


def read_weekdays() -> List[int]:
    """Ask for weekdays like 'mon, wed, fri' or 'weekdays'."""
    while True:
        text = input("Repeat on which days? (e.g. mon,wed,fri or 'weekdays'): ").strip().lower()
        if text in ("weekdays", "mon-fri"):
            return [0, 1, 2, 3, 4]
        parts = [p for p in re.split(r"[,\s]+", text) if p]
        days = [parse_weekday(p) for p in parts]
        if parts and all(d is not None for d in days):
            return sorted(set(days))  # type: ignore[arg-type]
        print("Please type weekday names such as mon,wed,fri.")


def read_requirement(name: str) -> Optional[bool]:
    """
    Ask about an equipment need. Returns:
      True  = MUST have it,  False = must NOT have it,  None = don't care (both are fine).
    """
    while True:
        print(f"{name}:")
        print("   1 = Must have")
        print("   2 = Must NOT have")
        print("   3 = Don't care (rooms with and without are both fine)")
        answer = input("   Choose [3]: ").strip()
        if answer in ("", "3"):
            return None
        if answer == "1":
            return True
        if answer == "2":
            return False
        print("   Please enter 1, 2 or 3.")


def describe_requirement(name: str, value: Optional[bool]) -> str:
    return {True: f"{name}: must have", False: f"{name}: must NOT have",
            None: f"{name}: don't care"}[value]


def describe_filters(room_type: Optional[str], min_capacity: int, projector: Optional[bool],
                     computers: Optional[bool], keyword: str = "") -> str:
    """One line that repeats the user's choices so the result can be checked."""
    parts = [f"type: {room_type or 'any'}", f"capacity: at least {min_capacity}",
             describe_requirement("projector", projector),
             describe_requirement("computers", computers)]
    if keyword:
        parts.append(f"text: '{keyword}'")
    return "Your filters -> " + " | ".join(parts)


def read_room_type() -> Optional[str]:
    while True:
        answer = input("Room type (classroom/laboratory/any) [any]: ").strip().lower()
        if answer in ("", "any"):
            return None
        if answer in ROOM_TYPES:
            return answer
        print("Please type classroom, laboratory or any.")


def read_when(app: SmartCampus) -> Optional[TimeWindow]:
    """Ask whether the room is needed right now or for a specific time."""
    while True:
        answer = input("When do you need the room? 1 = right now, 2 = a specific time [1]: ").strip()
        if answer in ("", "1"):
            return None
        if answer == "2":
            break
        print("Please enter 1 or 2.")
    day = read_day(app, "Day (today/tomorrow/weekday/date) [today]: ")
    start = read_time("Start time (e.g. 10:00 or 2:30pm): ")
    end = read_time("End time: ", allow_24=True)
    return app.make_window(day, start, end)


def describe_window(window: Optional[TimeWindow]) -> str:
    if window is None:
        return "right now"
    return (f"{DAY_NAMES[window.day.weekday()]} {window.day.isoformat()}, "
            f"{fmt_time(window.start)}-{fmt_time(window.end)}")


def choose_location(app: SmartCampus, prompt: str) -> Optional[str]:
    """Show valid IDs and ask until valid. Blank input cancels (returns None)."""
    print("\nCampus locations:")
    for loc in app.graph.locations.values():
        note = ""
        if app.graph.is_closed(loc.location_id):
            note = f"   [CLOSED - {app.graph.closed_buildings[loc.location_id]}]"
        print(f"  {loc.location_id:6} - {loc.name}{note}")
    while True:
        value = input(prompt + " (blank to cancel): ").strip().upper()
        if not value:
            return None
        if value in app.graph.locations:
            return value
        print("Unknown location ID. Please choose one from the list.")


def choose_room(app: SmartCampus, prompt: str = "Room ID") -> Optional[str]:
    """Ask until a valid room ID is typed. Blank input cancels (returns None)."""
    while True:
        value = input(f"{prompt} (blank to cancel): ").strip().upper()
        if not value:
            return None
        if value in app.rooms:
            return value
        print("Unknown room ID. Use option 2 to see all room IDs.")


# ---------------------------------------------------------------------------
# 10. MENUS
# ---------------------------------------------------------------------------

def menu_find_rooms(app: SmartCampus) -> None:
    print("\nSEARCH / FILTER ROOMS (press Enter to skip a question)")
    keyword = input("Text in room ID, room name or building name (e.g. 'lab', 'cse') [any]: ").strip()
    room_type = read_room_type()
    min_capacity = read_int("Minimum capacity [0]: ", 0, default=0)
    projector = read_requirement("Projector")
    computers = read_requirement("Computers")
    available_only = ask_yes_no("Show only rooms that are completely free?")
    window = read_when(app) if available_only else None
    results = app.find_rooms(room_type, min_capacity, projector, computers,
                             available_only, window, keyword)

    print("\n" + describe_filters(room_type, min_capacity, projector, computers, keyword))
    if keyword:
        needle = keyword.lower()
        places = [f"{loc.name} ({loc.location_id})" for loc in app.graph.locations.values()
                  if kmp_search(f"{loc.location_id} {loc.name}".lower(), needle)]
        if places:
            print("Campus locations matching the text: " + ", ".join(places))
    label = f" ({describe_window(window)})" if available_only else ""
    print(f"Matching rooms{label}: {len(results)}")
    if not results:
        print("No rooms match those requirements.")
        return
    for room in results:
        print(f"- {room.room_id}: {room.name} | {room.room_type} | capacity {room.capacity} | "
              f"building {room.building_id} | projector: {yes_no_text(room.has_projector)} | "
              f"computers: {yes_no_text(room.has_computers)}")
        print(f"    status right now: {app.status_text(room)}")


def menu_nearest_room(app: SmartCampus) -> None:
    origin = choose_location(app, "Start location ID")
    if origin is None:
        return
    room_type = read_room_type()
    capacity = read_int("Minimum capacity [0]: ", 0, default=0)
    projector = read_requirement("Projector")
    computers = read_requirement("Computers")
    window = read_when(app)
    eligible_count, results = app.nearest_available_room(
        origin, room_type, capacity, projector, computers, window
    )

    print("\n" + describe_filters(room_type, capacity, projector, computers))
    if eligible_count == 0:
        print(f"No completely free room matches those requirements ({describe_window(window)}).")
        return
    if not results:
        print("Free rooms exist, but none can be reached because of blocked pathways or closed buildings.")
        return
    print(f"\nFree rooms ({describe_window(window)}) ranked by walking distance:")
    for room, path, distance in results:
        names = " -> ".join(app.graph.locations[n].name for n in path)
        print(f"\n{room.room_id} - {room.name}  (capacity {room.capacity})")
        print(f"  Distance: {distance:.1f} m")
        print(f"  Route   : {names}")


def menu_route(app: SmartCampus) -> None:
    start = choose_location(app, "Start location ID")
    if start is None:
        return
    goal = choose_location(app, "Destination location ID")
    if goal is None:
        return
    path, distance = app.graph.a_star(start, goal)
    print("\nShortest walking route (A* search). Blocked pathways and closed buildings are avoided.")
    if path is None:
        print("No route exists. The destination may be cut off by blocked pathways or closed buildings.")
        return
    print("Route: " + " -> ".join(f"{n} ({app.graph.locations[n].name})" for n in path))
    print(f"Total walking distance: {distance:.1f} m")


def pick_reason(title: str, reasons: Tuple[str, ...]) -> str:
    print(title)
    for i, text in enumerate(reasons, start=1):
        print(f"  {i}. {text}")
    return reasons[read_int(f"Choose 1-{len(reasons)}: ", 1, len(reasons)) - 1]


def show_closures(app: SmartCampus) -> None:
    graph = app.graph
    print("\nCURRENT PATHWAY BLOCKS AND BUILDING CLOSURES")
    if not graph.blocked_edges and not graph.closed_buildings:
        print("Nothing is blocked or closed. All pathways and buildings are open.")
        return
    if graph.blocked_edges:
        print("Blocked pathways:")
        for edge, reason in graph.blocked_edges.items():
            a, b = sorted(edge)
            print(f"  {a} <-> {b}  - {reason}")
    if graph.closed_buildings:
        print("Closed buildings:")
        for location_id, reason in graph.closed_buildings.items():
            print(f"  {location_id} ({graph.locations[location_id].name})  - {reason}")


def menu_block_path(app: SmartCampus) -> None:
    while True:
        print("\nBLOCK / REOPEN - pathways and buildings")
        print("  PATHWAY block   : a road between TWO locations is blocked (road work, flooding...).")
        print("                    The buildings stay open; people must go around.")
        print("  BUILDING closure: a WHOLE building is closed (e.g. under construction).")
        print("                    Nobody can enter or walk through it and its rooms become unavailable.")
        print("1. Block or reopen a PATHWAY (road between two locations)")
        print("2. Close or reopen a whole BUILDING")
        print("3. Show everything currently blocked or closed")
        print("4. Back to main menu")
        choice = input("Choose: ").strip()

        if choice == "1":
            a = choose_location(app, "First location ID")
            if a is None:
                continue
            b = choose_location(app, "Second location ID")
            if b is None:
                continue
            if not app.graph.has_path(a, b):
                direct = ", ".join(n for n, _ in app.graph.adj[a]) or "none"
                print("Those locations do not have a direct pathway "
                      "(a pathway joins two neighbouring locations only).")
                print(f"Locations directly joined to {a}: {direct}")
                continue
            if app.graph.is_blocked(a, b):
                reason = app.graph.block_reason(a, b)
                if ask_yes_no(f"This pathway is BLOCKED ({reason}). Reopen it?"):
                    print(app.change_path_state(a, b, False))
            elif ask_yes_no("This pathway is OPEN. Block it?"):
                reason = pick_reason("Why is it blocked?", PATH_BLOCK_REASONS)
                print(app.change_path_state(a, b, True, reason))
        elif choice == "2":
            building = choose_location(app, "Building ID")
            if building is None:
                continue
            name = app.graph.locations[building].name
            if app.graph.is_closed(building):
                reason = app.graph.closed_buildings[building]
                if ask_yes_no(f"{name} is CLOSED ({reason}). Reopen it?"):
                    print(app.change_building_state(building, False))
            elif ask_yes_no(f"{name} is OPEN. Close the whole building?"):
                reason = pick_reason("Why is it closed?", BUILDING_CLOSE_REASONS)
                print(app.change_building_state(building, True, reason))
        elif choice == "3":
            show_closures(app)
        elif choice == "4":
            return
        else:
            print("Invalid choice.")


def menu_room_control(app: SmartCampus) -> None:
    room_id = choose_room(app)
    if room_id is None:
        return
    room = app.rooms[room_id]
    print(f"\n{room.room_id} - {room.name}: {app.status_text(room)}; "
          f"capacity {room.capacity}; "
          f"available: {yes_no_text(app.is_available_now(room))}")
    print("1. People enter (booked class arrives, or a walk-in session)")
    print("2. End the session (everyone has left)")
    print("3. Take the room out of service / return it to service")
    print("4. Correct the head-count of the running session")
    print("5. Simulate a sensor update")
    choice = input("Choose: ").strip()

    if choice == "1":
        if app.graph.is_closed(room.building_id):
            print(f"Cannot enter: building {room.building_id} is CLOSED "
                  f"({app.graph.closed_buildings[room.building_id]}).")
            return
        if not room.in_service:
            print(f"Cannot enter: {room.room_id} is out of service.")
            return
        if room.occupied > 0:
            print(f"Cannot enter: {room.room_id} is in use by {room.occupied} people. "
                  "Only a completely free room can be used.")
            return
        active = app.active_booking(room_id)
        if active:
            print(f"This room is booked for '{active.title}' until {fmt_time(active.end)}. "
                  "Recording that class arriving.")
            count = read_int(f"People who arrived (1-{room.capacity}): ", 1, room.capacity)
            app.start_session(room_id, count)
            print(f"{room.room_id} is now IN USE.")
        else:
            count = read_int(f"Number of people (1-{room.capacity}): ", 1, room.capacity)
            nxt = app.next_booking_today(room_id)
            if nxt:
                print(f"Note: the next booking starts at {fmt_time(nxt.start)}.")
            minutes = read_int("How many minutes will you need? ", 1, MINUTES_PER_DAY)
            booking = app.start_session(room_id, count, minutes)
            print(f"Walk-in session booked {fmt_time(booking.start)}-{fmt_time(booking.end)}. "
                  f"{room.room_id} is unavailable to others until then.")
    elif choice == "2":
        status = app.end_session(room_id)
        print(f"Session ended. {room.room_id} is now: {status}")
    elif choice == "3":
        if room.in_service:
            if room.occupied and not ask_yes_no(f"{room.occupied} people are inside. Take it out of service anyway?"):
                print("Cancelled.")
                return
            app.set_in_service(room_id, False)
            print(f"{room.room_id} is now OUT OF SERVICE.")
        else:
            app.set_in_service(room_id, True)
            print(f"{room.room_id} is back in service.")
    elif choice == "4":
        if room.occupied == 0:
            print("No session is running in this room.")
            return
        count = read_int(f"New head-count (0 ends the session, max {room.capacity}): ", 0, room.capacity)
        app.adjust_headcount(room_id, count)
        print("Head-count updated.")
    elif choice == "5":
        r = app.simulate_sensor_update(room_id)
        print(f"Simulated reading: {r.temperature_c} C, {r.energy_kwh} kWh, {r.occupancy} people "
              f"-> {app.status_text(room)}")
    else:
        print("Invalid choice.")


def menu_book_room(app: SmartCampus) -> None:
    room_id = choose_room(app)
    if room_id is None:
        return
    room = app.rooms[room_id]
    if not room.in_service:
        print(f"{room_id} is out of service and cannot be booked.")
        return
    title = input("Class/event title: ").strip()
    if not title:
        print("A title is required.")
        return
    start = read_time("Start time (e.g. 10:00 or 2:30pm): ")
    end = read_time("End time: ", allow_24=True)
    if end <= start:
        print("The end time must be after the start time.")
        return
    people = read_int(f"Number of people (1-{room.capacity}): ", 1, room.capacity)

    if ask_yes_no("Repeat every week?"):
        created = app.add_weekly_bookings(room_id, title, start, end, people, read_weekdays())
    else:
        day = read_day(app, "Date (today/tomorrow/weekday/date) [today]: ")
        created = [app.add_booking(room_id, title, start, end, people, day=day)]
    print(f"\nBooked {len(created)} slot(s):")
    for booking in created:
        print("  " + booking.summary())


def menu_cancel_booking(app: SmartCampus) -> None:
    room_id = choose_room(app)
    if room_id is None:
        return
    app.print_room_timetable(room_id)
    text = input("Booking number to cancel, e.g. 5 (blank to cancel): ").strip().lstrip("#")
    if not text:
        return
    if not text.isdigit():
        print("Please enter the booking number shown in [#...].")
        return
    booking = app.bookings.get(int(text))
    if booking is None or booking.room_id != room_id:
        print("That booking does not belong to this room.")
        return
    if ask_yes_no(f"Cancel '{booking.title}' ({booking.when_text()}, "
                  f"{fmt_time(booking.start)}-{fmt_time(booking.end)})?"):
        app.cancel_booking(booking.booking_id)
        print("Booking cancelled.")


def menu_timetable(app: SmartCampus) -> None:
    while True:
        print("\nTIMETABLE AND ROOM BOOKING")
        print("1. View one room's timetable")
        print("2. View the schedule of all rooms for a day")
        print("3. Book a room (weekly or one-off)")
        print("4. Cancel a booking")
        print("5. Back to main menu")
        print("(To find rooms free at a certain time, use main-menu options 3 and 4.)")
        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                room_id = choose_room(app)
                if room_id:
                    app.print_room_timetable(room_id)
            elif choice == "2":
                app.print_day_schedule(read_day(app, "Day (today/tomorrow/weekday/date) [today]: "))
            elif choice == "3":
                menu_book_room(app)
            elif choice == "4":
                menu_cancel_booking(app)
            elif choice == "5":
                return
            else:
                print("Invalid choice.")
        except ValueError as error:
            print(f"Could not complete that: {error}")


def menu_clock(app: SmartCampus) -> None:
    print("\nSYSTEM CLOCK (real or simulated time)")
    print("-" * 72)
    print("The program uses the clock to decide which classes are running RIGHT NOW,")
    print("which rooms are free, and when a walk-in session ends.")
    print("  * Real clock      : your computer's actual date and time (the default).")
    print("  * Simulated clock : YOU pick a day and time (e.g. Monday 10:30) and the")
    print("    program behaves as if it were that moment. The simulated time is FROZEN:")
    print("    it does not move forward until you switch back to the real clock.")
    print("    Use it to demo or test the timetable without waiting for a real class.")
    print("-" * 72)
    print(f"Currently using: {app.time_text()}")
    print("1. Simulate a day and time")
    print("2. Switch back to the real clock")
    print("3. Back")
    choice = input("Choose: ").strip()
    if choice == "1":
        day = read_day(app, "Day to pretend it is (today/tomorrow/weekday/date) [today]: ")
        minutes = read_time("Time to pretend it is (e.g. 10:30 or 2:30pm): ")
        app.set_clock(dt.datetime.combine(day, dt.time(minutes // 60, minutes % 60)))
        free, busy, unavailable = app.room_counts()
        print(f"\nClock is now frozen at: {app.time_text()}")
        print(f"At that moment: {free} room(s) free, {busy} busy/reserved, "
              f"{unavailable} unavailable (out of service or building closed).")
        print("Use main-menu option 2 to see every room's status at this time.")
    elif choice == "2":
        app.set_clock(None)
        print(f"Now using the real clock: {app.time_text()}")
    elif choice != "3":
        print("Invalid choice.")


def menu_energy(app: SmartCampus) -> None:
    while True:
        order = app.energy_building_order
        print("\nBUILDING ENERGY CONSUMPTION")
        for i, b in enumerate(order, start=1):
            print(f"  {i}. {b:5} ({app.graph.locations[b].name}): {app.building_energy[b]:.2f} kWh")
        print(f"  Total energy of all buildings: {app.total_energy():.2f} kWh")
        print("\n1. Update one building's reading")
        print("2. Add up the energy of a range of buildings (by list number)")
        print("3. Back to main menu")
        choice = input("Choose: ").strip()

        if choice == "1":
            building_id = input("Building ID: ").strip().upper()
            if building_id not in app.graph.locations:
                print("Unknown building ID.")
                continue
            app.update_building_energy(building_id, read_float("New energy reading (kWh): ", 0.0))
            print("Energy value updated.")
        elif choice == "2":
            n = len(order)
            if n == 0:
                print("No buildings are indexed.")
                continue
            print("Pick the first and last building NUMBER from the list above.")
            print("Every building from the first to the last (inclusive) is added up.")
            left = read_int(f"First building number (1-{n}): ", 1, n)
            right = read_int(f"Last building number ({left}-{n}): ", left, n)
            total = app.energy_between_positions(left, right)
            print(f"\nBuildings included (#{left} to #{right}):")
            direct = 0.0
            for i in range(left, right + 1):
                value = app.building_energy[order[i - 1]]
                direct += value
                print(f"  #{i} {order[i - 1]:5} {value:9.2f} kWh")
            upto_right = app.energy_tree.prefix_sum(right)
            upto_before = app.energy_tree.prefix_sum(left - 1)
            print("\n(prefix(k) = total of buildings #1 to #k, kept by the Fenwick tree)")
            print(f"Range total = prefix({right}) - prefix({left - 1}) "
                  f"= {upto_right:.2f} - {upto_before:.2f} = {total:.2f} kWh")
            verdict = "matches" if abs(direct - total) < 1e-6 else "DOES NOT MATCH - please report this"
            print(f"Check: adding the values above one by one gives {direct:.2f} kWh ({verdict}).")
            print(f"Average per building: {total / (right - left + 1):.2f} kWh")
        elif choice == "3":
            return
        else:
            print("Invalid choice.")


def menu_nearest_location(app: SmartCampus) -> None:
    x = read_float("Your map X coordinate: ")
    y = read_float("Your map Y coordinate: ")
    nearest = app.kd_tree.nearest(x, y)
    if nearest is None:
        print("No campus locations are indexed.")
        return
    location_id, distance = nearest
    print(f"Nearest location: {app.graph.locations[location_id].name} ({location_id}), "
          f"{distance:.2f} map units away (straight line, not walking distance).")
    if app.graph.is_closed(location_id):
        print(f"Note: it is currently CLOSED ({app.graph.closed_buildings[location_id]}).")


def menu_connectivity(app: SmartCampus) -> None:
    print("\nCHECK THE CONNECTION BETWEEN TWO LOCATIONS")
    print("Possible results:")
    print("  - same location")
    print("  - directly connected (one open pathway)")
    print("  - indirectly connected (you walk through other locations)")
    print("  - connected only by going around a blocked pathway")
    print("  - not connected (blocked pathways cut the campus into separate parts)")
    print("  - not connected (one of the buildings is closed)")
    a = choose_location(app, "First location ID")
    if a is None:
        return
    b = choose_location(app, "Second location ID")
    if b is None:
        return
    print()
    for line in app.describe_connection(a, b):
        print(line)


def menu_open_pathways(app: SmartCampus) -> None:
    rows = app.graph.all_pathways()
    open_rows = [r for r in rows if r[3] == "OPEN"]
    print("\nOPEN PATHWAYS AVAILABLE")
    print("-" * 72)
    for a, b, distance, status in rows:
        print(f"  {a:6} <-> {b:6} {distance:6.1f} m   {status}")
    print("-" * 72)
    print(f"{len(open_rows)} of {len(rows)} pathways are open right now.")
    if app.graph.closed_buildings:
        closed = ", ".join(app.graph.closed_buildings)
        print(f"Closed buildings (cannot be entered or crossed): {closed}")
    if not open_rows:
        print("No pathway is open.")
        return

    mst = app.graph.minimum_spanning_tree()
    print("\nMINIMUM NETWORK (Kruskal's algorithm)")
    print("The shortest set of open pathways that still keeps every reachable location connected:")
    for a, b, weight in mst:
        print(f"  {a:6} <-> {b:6} {weight:6.1f} m")
    minimum_total = sum(w for _, _, w in mst)
    all_total = sum(r[2] for r in open_rows)
    print(f"Minimum network length: {minimum_total:.1f} m   (all open pathways together: {all_total:.1f} m)")
    print(f"The other {len(open_rows) - len(mst)} open pathway(s) are extra routes: "
          "shortcuts, or alternatives if one of the pathways above gets blocked.")
    parts = app.graph.connectivity().component_count()
    if parts > 1:
        print(f"Warning: the open network is split into {parts} separate parts, "
              "so the result is a set of trees (a forest), not one tree.")


def menu_alerts(app: SmartCampus) -> None:
    print("\nCAMPUS ALERTS")
    print("Alerts are warnings the system raises by itself, for example: a blocked pathway,")
    print("a closed building, a full room, people in a room with no booking, or high temperature.")
    print("Levels, most urgent first: CRITICAL (act now), HIGH, MEDIUM, INFO (just so you know).")
    while True:
        app.show_alerts()
        if not app.alerts.show_alerts():
            return
        if not ask_yes_no("Mark the most urgent alert as handled (it is removed from the list)?"):
            return
        app.process_next_alert()


MENU_TEXT = """
========================================================================
 SMART CAMPUS DIGITAL TWIN - MAIN MENU
========================================================================
  1. Campus summary
  2. List classrooms and laboratories (live status)
  3. Search/filter rooms (text, equipment, free now or at a chosen time)
  4. Find nearest FREE room (now or at a chosen time)
  5. Find the shortest route between two locations
  6. Block/reopen a pathway or close/reopen a building
  7. Room control (people enter/leave, maintenance, sensors)
  8. View sensor readings
  9. Energy management
 10. Find nearest campus location to a map point
 11. Check the connection between two locations
 12. Open pathways available
 13. Campus alerts (view / mark as handled)
 14. Timetable and room booking
 15. System clock (use real time or simulate a day/time)
  0. Exit
========================================================================"""


def main() -> None:
    app = SmartCampus()
    print("Welcome! A sample campus with a weekly timetable has been loaded.")
    actions = {
        "1": app.campus_summary,
        "2": app.list_rooms,
        "3": lambda: menu_find_rooms(app),
        "4": lambda: menu_nearest_room(app),
        "5": lambda: menu_route(app),
        "6": lambda: menu_block_path(app),
        "7": lambda: menu_room_control(app),
        "8": app.sensor_report,
        "9": lambda: menu_energy(app),
        "10": lambda: menu_nearest_location(app),
        "11": lambda: menu_connectivity(app),
        "12": lambda: menu_open_pathways(app),
        "13": lambda: menu_alerts(app),
        "14": lambda: menu_timetable(app),
        "15": lambda: menu_clock(app),
    }
    while True:
        print(MENU_TEXT)
        print(f" Time now: {app.time_text()}")
        try:
            choice = input("Enter your choice: ").strip()
            if choice == "0":
                break
            action = actions.get(choice)
            if action is None:
                print("Invalid choice. Enter a number from 0 to 15.")
            else:
                action()
        except (ValueError, KeyError, IndexError) as error:
            print(f"Operation could not be completed: {error}")
        except (EOFError, KeyboardInterrupt):
            print()
            break
    print("Thank you for using Smart Campus Digital Twin.")


if __name__ == "__main__":
    main()
