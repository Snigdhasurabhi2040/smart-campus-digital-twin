def show_building_energy(self) -> None:
    for b, energy in self.building_energy.items():
        print(f"{b}: {fmt_energy(energy)}")
