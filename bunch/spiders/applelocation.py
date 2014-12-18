from scrapy.spider import Spider
from scrapy.http import Request
from scrapy.contrib.linkextractors import LinkExtractor

from bunch.items import LocationItem

import re

from __init__ import get_hours_item_value

class AppleLocationSpider(Spider):
    name = 'apple'
    allowed_domains = ['www.apple.com']
    start_urls = ['http://www.apple.com/retail/storelist/']
    
    meta_first = 'apple_location_spider_first'
    meta_country = 'apple_location_spider_country'
    meta_url = 'apple_location_spider_url'
    
    hours_countries = ['United States']
    hours_full_year = '24/7, 365 days a year'  
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, meta={self.meta_first: True}, dont_filter=True)

    def parse(self, response):
        if self.meta_first in response.meta: #start page with links
            for menuitem in response.xpath('//section[@id="country_switcher"]/div/ul/li'):
                code = menuitem.xpath('@data-tag')[0].extract()
                name = menuitem.xpath('text()')[0].extract()
                for link in [l for l in LinkExtractor(restrict_xpaths='//div[@id="%s"]/div/ul/li/a' % (code+'stores')).extract_links(response)][:1]:
                    yield Request(link.url, callback=self.parse, meta={self.meta_country: name, self.meta_url: link.url})
                    
        else: #scraping of items
            item = LocationItem()
            address = response.xpath('(//address)[1]')
            
            city = address.xpath('.//span[@class="locality"]/text()').extract()
            if len(city): item['city'] = city[0]
            item['address'] = [s.strip() for s in address.xpath('div[@class="street-address"]/text()').extract()]
            item['country'] = response.meta[self.meta_country]
            if item['country'] in self.hours_countries:
                item['hours'] = self.parse_hours(address.xpath('../table[@class="store-info"]/tr'))
            item['phone_number'] = address.xpath('div[@class="telephone-number"]/text()')[0].extract().strip()
            item['services'] = response.xpath('//nav[@class="nav hero-nav selfclear"]//img/@alt').extract()
            state = address.xpath('.//span[@class="region"]/text()').extract()
            if len(state): item['state'] = state[0]
            #todo: find store_email if it exists
            #todo: find store_floor_plan_url if it exists
            item['store_image_url'] = address.xpath('../../div[@class="column last"]/img/@src')[0].extract()
            item['store_name'] = address.xpath('div[@class="store-name"]/text()')[0].extract().strip()
            #todo: find store_id if it exists
            #todo: find weekly_ad_url if it exists
            item['store_id'] = item['weekly_ad_url'] = item['store_url'] = response.meta[self.meta_url]
            zipcode = address.xpath('.//span[@class="postal-code"]/text()').extract()
            if len(zipcode): item['zipcode'] = zipcode[0]
            yield item
            
    def parse_hours(self, trs):
        trs = trs[1:]
        trs = [(tr.xpath('td/text()')[0].extract(), tr.xpath('td/text()')[1].extract()) for tr in trs]
        
        if trs[0][0] == self.hours_full_year:
            return days_dict([('12:00 a.m','12:00 a.m') for x in range(7)])
        else:
            sitedays = ['Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            days = {}
            for tr in trs:
                idxes = None
                if ' - ' in tr[0]: #interval of days
                    words = re.split('\W+', tr[0])
                    start = words[0]
                    end = words[1]
                    idxes = range(sitedays.index(start), sitedays.index(end)+1)
                else: #single day
                    words = re.split('\W+', tr[0])
                    idxes = [sitedays.index(words[0])]
                for i in idxes:
                    days[i] = tr[1].split(' - ')
            return get_hours_item_value(days)
