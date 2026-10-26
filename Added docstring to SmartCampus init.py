def print_pathways(self) -> None:
    for a, b, dist, status in self.graph.all_pathways():
        print(f"{a} <-> {b}: {dist} m [{status}]")
