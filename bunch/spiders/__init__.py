# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

_week = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}

def get_hours_item_value(days_time_pairs):
    days = {}
    for idx in _week:
        if idx in days_time_pairs:
            open, close = days_time_pairs[idx]
            days[_week[idx]] = {'open': open, 'close': close}
    return days
