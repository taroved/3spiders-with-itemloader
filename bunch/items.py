# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field

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
    