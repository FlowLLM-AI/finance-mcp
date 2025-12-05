import datetime


def get_datetime(time_ft: str = "%Y-%m-%d %H:%M:%S"):
    now = datetime.datetime.now()
    formatted_time = now.strftime(time_ft)
    return formatted_time
