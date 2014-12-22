from scrapy.spider import Spider
from scrapy.http import Request, FormRequest
from scrapy.contrib.linkextractors import LinkExtractor

from bunch.items import LocationItem

from __init__ import get_hours_item_value

class WetsealLocationSpider(Spider):
    name = 'wetseal'
    allowed_domains = ['www.wetseal.com']
    start_urls = ['http://www.wetseal.com/Stores']

    meta_first = 'wetseal_location_spider_first'
    meta_state = 'wetseal_location_spider_state'
    
    country = 'United States' # I suppose there is only US 

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, meta={self.meta_first: True}, dont_filter=True)

    def parse(self, response):
        if self.meta_first in response.meta: #start page with states list
            formxpath = '//form[@id="dwfrm_storelocator_state"]'
            form = response.xpath(formxpath)[0]
            select_name = form.xpath('.//select/@name')[0].extract()
            button_name = form.xpath('.//button/@name')[0].extract() #scrapy ignores button tag in FormRequest._get_clickable. Should it do it?
            button_value = form.xpath('.//button/@value')[0].extract()
            for option in form.xpath('.//select/option')[1:]:
                code = option.xpath('@value')[0].extract()
                name = option.xpath('text()')[0].extract()
                yield FormRequest.from_response(response, callback=self.parse,
                                  formdata={select_name: code, button_name: button_value},
                                  formxpath=formxpath,
                                  meta={self.meta_state: name})
        
        else:#get items
            for tr in response.xpath('//table[@id="store-location-results"]/tbody/tr'):
                item = LocationItem()
                
                address_lines = tr.xpath('td[@class="store-address"]/text()')
                item['phone_number'] = address_lines.pop().extract().strip()
                city_zipcode = address_lines.pop()
                if city_zipcode.re('\s*([^,]+), \w+ (\d+)'):
                    item['city'], item['zipcode'] = city_zipcode.re('\s*([^,]+), \w+ (\d+)')
                else:
                    item['city'] = city_zipcode.re('\s*([^,]+), \w+')
                
                #todo: find services if it exists
                item['address'] = [l.strip() for l in address_lines.extract()]
                item['country'] = self.country
                item['hours'] = self.parse_hours(tr.xpath('.//div[@class="store-hours"]/text()'))
                item['state'] = response.meta[self.meta_state]
                item['store_name'] = tr.xpath('.//div[@class="store-name"]/text()')[0].extract().strip()
                #todo: find store_email if it exists
                #todo: find store_floor_plan_url if it exists
                #import pdb; pdb.set_trace()
                item['store_id'] = tr.xpath('.//div[@class="store-name"]/../@id')[0].extract()
                #todo: find store_image_url if it exists
                item['store_url'] = LinkExtractor(restrict_xpaths='//a[@id="%s"]' % item['store_id']).extract_links(response)[0].url
                #todo: find weekly_ad_url if it exists
                yield item

    def parse_hours(self, lines):
        sitedays = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Fri': 4, 'Saturday': 5, 'Sunday': 6}
        days = {}
        for l in lines:
            pieces = l.re('(\w+)-(\w+):\s*(\d+:\d+ \w+) - (\d+:\d+ \w+)')
            idxes = []
            if pieces: #interval
                start = pieces.pop(0)
                end = pieces.pop(0)
                idxes = range(sitedays[start], sitedays[end]+1)
            else: #single day
                pieces = l.re('(\w+):\s*(\d+:\d+ \w+) - (\d+:\d+ \w+)')
                if pieces:
                    idxes = [sitedays[pieces.pop(0)]]
            for i in idxes:
                days[i] = pieces
        return get_hours_item_value(days)