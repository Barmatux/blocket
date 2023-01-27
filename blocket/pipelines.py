# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import pymongo as pymongo
from googletrans import Translator
from itemadapter import ItemAdapter

from blocket.items import AdItem


class MongoPipeline:

    collection_name = 'blocket'

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'items')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        ad_item = AdItem(item)
        self.db[self.collection_name].update_one({'_id': ad_item.get('_id')}, {"$set": dict(ad_item)}, upsert=True)
        return item

class TranslatedPipeline:
    def __init__(self):
        self.translator = Translator()

    def process_item(self, item, spider):
        translated_description = self.translator.translate(item.get('description'), src='sv', dest='ru')
        item['description'] = translated_description.text
        # if item.get('features_list'):
        #     item['features_list'] = [self.translator.translate(i, src='sv', dest='ru').text for i in item.get('features_list')]
        return item
