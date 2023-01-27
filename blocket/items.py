# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class AdItem(scrapy.Item):
    _id = scrapy.Field()
    description = scrapy.Field()
    fuel = scrapy.Field()
    title = scrapy.Field()
    make = scrapy.Field()
    model = scrapy.Field()
    year = scrapy.Field()
    date = scrapy.Field()
    price = scrapy.Field()
    url = scrapy.Field()
    distance = scrapy.Field()
    features_list = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
    price_ex_vat = scrapy.Field()
    vat =scrapy.Field()
    engine = scrapy.Field()
    date_in_traffic = scrapy.Field()
