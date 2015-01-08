# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field
from scrapy.contrib.loader import ItemLoader
from scrapy.contrib.loader.processor import TakeFirst, Identity, Compose


class LocationItem(Item):
    city = Field()
    address = Field()
    country = Field()
    hours = Field()
    phone_number = Field()
    services = Field()
    state = Field()
    store_email = Field()
    store_floor_plan_url = Field()
    store_id = Field()
    store_image_url = Field()
    store_name = Field()
    store_url = Field()
    weekly_ad_url = Field()
    zipcode = Field()


class ProductItem(Item):
    currency = Field()
    current_price = Field()
    original_price = Field()
    description = Field()
    brand = Field()
    title = Field()
    retailer_id = Field()
    model = Field()
    mpn = Field()
    sku = Field()
    upc = Field()
    image_urls = Field()
    primary_image_url = Field()
    features = Field()
    specifications = Field()
    trail = Field()
    rating = Field()
    available_instore = Field()
    available_online = Field()


_week = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday',
         3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}


def _get_hours_item_value(time_pairs):
    days = {}
    for idx in _week:
        if idx in time_pairs:
            open, close = time_pairs[idx]
            days[_week[idx]] = {'open': open, 'close': close}
    return days


class LocationLoader(ItemLoader):
    default_item_class = LocationItem

    default_output_processor = TakeFirst()
    address_out = Identity()
    hours_out = Compose(lambda x: x[0], _get_hours_item_value)
    services_out = Identity()
