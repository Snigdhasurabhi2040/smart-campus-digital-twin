if __name__ == "__main__":
    campus = SmartCampus()
    print("Campus initialized with sample data.")
    campus.refresh_sensors()
    campus.show_alerts_pretty()
