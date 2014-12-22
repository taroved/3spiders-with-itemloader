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
                for link in [l for l in LinkExtractor(restrict_xpaths='//div[@id="%s"]/div/ul/li/a' % (code+'stores')).extract_links(response)]:
                    yield Request(link.url, callback=self.parse, meta={self.meta_country: name})
                    
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
            #store_email: not found
            #store_floor_plan_url: not found
            item['store_image_url'] = address.xpath('../../div[@class="column last"]/img/@src')[0].extract()
            item['store_name'] = address.xpath('div[@class="store-name"]/text()')[0].extract().strip()
            item['store_id'] = response.xpath('/html/head/meta[@name="omni_page"]/@content').re('(R\d+)$')[0]
            #find weekly_ad_url: on the same page
            item['weekly_ad_url'] = item['store_url'] = response.url
            zipcode = address.xpath('.//span[@class="postal-code"]/text()').extract()
            if len(zipcode): item['zipcode'] = zipcode[0]
            yield item
            
    def parse_hours(self, trs):
        trs = trs[1:]
        rows = [tr.xpath('td/text()') for tr in trs]

        if rows[0][0].extract() == self.hours_full_year:
            return get_hours_item_value([('12:00 a.m','12:00 a.m') for x in range(7)])
        else:
            sitedays = ['Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            
            days = {}
            for row in rows:
                day_interval = row[0]
                time_interval = row[1].extract()
                
                day_idxes = None
                pieces = day_interval.re('(\w+) - (\w+)')
                if pieces: #interval of days
                    day_idxes = range(sitedays.index(pieces[0]), sitedays.index(pieces[1])+1)
                else: #single day
                    d = day_interval.re('\w+')[0]
                    day_idxes = [sitedays.index(d)]
                
                if ' - ' in time_interval:
                    time_interval = time_interval.split(' - ')
                elif time_interval == 'Closed':
                    continue
                     
                for i in day_idxes:
                    days[i] = time_interval
            return get_hours_item_value(days)
