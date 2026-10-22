class DisjointSetUnion:
    def __init__(self, items):
        self.parent = {i:i for i in items}
    def find(self, x):
        while self.parent[x] != x:
            x = self.parent[x]
        return x
    def union(self,a,b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

class CampusGraph:
    def __init__(self):
        self.locations = {}
        self.adj = {}
    def add_location(self, loc):
        self.locations[loc.location_id] = loc
        self.adj.setdefault(loc.location_id, [])
    def add_path(self,a,b,distance):
        self.adj[a].append((b,distance))
        self.adj[b].append((a,distance))
