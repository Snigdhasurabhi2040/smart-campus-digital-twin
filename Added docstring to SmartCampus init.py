def clear_alerts(self) -> None:
    while self.alerts.pop_alert():
        pass
