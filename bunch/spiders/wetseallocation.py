from scrapy.contrib.spiders import CrawlSpider
from scrapy.http import FormRequest
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.contrib.loader.processor import TakeFirst

from bunch.items import LocationLoader


class WetsealLocationSpider(CrawlSpider):
    name = 'wetseal'
    allowed_domains = ['www.wetseal.com']
    start_urls = ['http://www.wetseal.com/Stores']

    meta_state = 'wetseal_location_spider_state'

    country = 'United States'  # I suppose there is only US

    def parse_start_url(self, response):
        """Parse start page with states list.

        @url http://www.wetseal.com/Stores
        @returns requests 23
        """
        formxpath = '//form[@id="dwfrm_storelocator_state"]'
        form = response.xpath(formxpath)[0]
        select_name = form.xpath('.//select/@name')[0].extract()
        # scrapy ignores button tag in FormRequest._get_clickable. Should
        # it do it?
        button_name = form.xpath('.//button/@name')[0].extract()
        button_value = form.xpath('.//button/@value')[0].extract()
        for option in form.xpath('.//select/option')[1:]:
            code = option.xpath('@value')[0].extract()
            name = option.xpath('text()')[0].extract()
            yield FormRequest.from_response(response, callback=self.parse_stores,
                                            formdata={
                                                select_name: code, button_name: button_value},
                                            formxpath=formxpath,
                                            meta={self.meta_state: name})

    def parse_stores(self, response):
        """Parse items"""
        for tr in response.xpath('//table[@id="store-location-results"]/tbody/tr'):
            il = LocationLoader(response=response)

            address_lines = tr.xpath('td[@class="store-address"]/text()')
            il.add_value('phone_number', address_lines.pop().extract().strip())
            city_zipcode = address_lines.pop().extract()
            il.add_value('city', city_zipcode, re=r'\s*([^,]+), \w+')
            il.add_value('zipcode', city_zipcode, re=r'\s*[^,]+, \w+ (\d+)')

            # services: not found
            il.add_value('address', address_lines,
                         lambda x: [s.strip() for s in x.extract()])

            il.add_value('country', self.country)

            il.add_value('hours',
                         tr.xpath('.//div[@class="store-hours"]/text()'),
                         self.parse_hours)
            il.add_value('state', response.meta[self.meta_state])

            il.selector = tr
            il.add_xpath('store_name', './/div[@class="store-name"]/text()',
                         TakeFirst(), unicode.strip)
            # store_email: not found
            # store_floor_plan_url: not found
            il.add_xpath('store_id', './/div[@class="store-name"]/../@id')
            # store_image_url: not found
            store_id = il.get_collected_values('store_id')[0]
            il.add_value('store_url',
                         LinkExtractor(
                             restrict_xpaths='//a[@id="%s"]' % store_id).extract_links(response)[0].url)
            # weekly_ad_url: not found

            yield il.load_item()

    def parse_hours(self, lines):
        sitedays = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2,
                    'Thursday': 3, 'Friday': 4, 'Fri': 4, 'Saturday': 5, 'Sunday': 6}
        days = {}
        for ln in lines:
            pieces = ln.re(r'(\w+)-(\w+):\s*(\d+:\d+ \w+) - (\d+:\d+ \w+)')
            idxes = []
            if pieces:  # interval
                start = pieces.pop(0)
                end = pieces.pop(0)
                idxes = range(sitedays[start], sitedays[end] + 1)
            else:  # single day
                pieces = ln.re(r'(\w+):\s*(\d+:\d+ \w+) - (\d+:\d+ \w+)')
                if pieces:
                    idxes = [sitedays[pieces.pop(0)]]
            for i in idxes:
                days[i] = pieces
        return days
