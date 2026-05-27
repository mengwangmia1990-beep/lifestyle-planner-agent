from datetime import datetime, timedelta

def parse_time(time_str: str):
    time = datetime.strptime(time_str, "%H:%M")
    return time


def add_minutes(start_time: datetime, duration: int) -> datetime:
     return start_time + timedelta(minutes=duration)