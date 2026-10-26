def print_mst(self) -> None:
    mst = self.graph.minimum_spanning_tree()
    for a, b, w in mst:
        print(f"{a} -- {b} ({w:.1f} m)")
