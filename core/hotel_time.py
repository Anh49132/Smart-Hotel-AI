from datetime import datetime, timedelta, timezone

HOTEL_TIMEZONE = timezone(timedelta(hours=7), name='Asia/Bangkok')


def hotel_now():
    return datetime.now(HOTEL_TIMEZONE)


def hotel_today():
    return hotel_now().date()
