from scrapy.contrib.spiders import CrawlSpider
from scrapy.http import Request
from scrapy.contrib.linkextractors import LinkExtractor

from bunch.items import LocationItem
from . import get_hours_item_value


class AppleLocationSpider(CrawlSpider):
    name = 'apple'
    allowed_domains = ['www.apple.com']
    start_urls = ['http://www.apple.com/retail/storelist/']

    meta_country = 'apple_location_spider_country'

    hours_countries = ['United States']
    hours_full_year = '24/7, 365 days a year'

    def parse_start_url(self, response):
        """Parse start page with links"""
        for menuitem in response.xpath('//section[@id="country_switcher"]/div/ul/li'):
            code = menuitem.xpath('@data-tag')[0].extract()
            name = menuitem.xpath('text()')[0].extract()
            path = '//div[@id="%s"]/div/ul/li/a' % (code + 'stores')
            for link in LinkExtractor(restrict_xpaths=path).extract_links(response):
                yield Request(link.url, callback=self.parse_store, meta={self.meta_country: name})

    def parse_store(self, response):
        """Scraping of items"""
        item = LocationItem()
        address = response.xpath('(//address)[1]')

        city = address.xpath('.//span[@class="locality"]/text()').extract()
        if len(city):
            item['city'] = city[0]
        item['address'] = [s.strip() for s in address.xpath(
            'div[@class="street-address"]/text()').extract()]
        item['country'] = response.meta[self.meta_country]
        if item['country'] in self.hours_countries:
            item['hours'] = self.parse_hours(
                address.xpath('../table[@class="store-info"][1]/tr'))
        item['phone_number'] = address.xpath(
            'div[@class="telephone-number"]/text()')[0].extract().strip()
        item['services'] = response.xpath(
            '//nav[@class="nav hero-nav selfclear"]//img/@alt').extract()
        state = address.xpath('.//span[@class="region"]/text()').extract()
        if len(state):
            item['state'] = state[0]
        # store_email: not found
        # store_floor_plan_url: not found
        item['store_image_url'] = address.xpath(
            '../../div[@class="column last"]/img/@src')[0].extract()
        item['store_name'] = address.xpath(
            'div[@class="store-name"]/text()')[0].extract().strip()
        item['store_id'] = response.xpath(
            '/html/head/meta[@name="omni_page"]/@content').re(r'(R\d+)$')[0]
        # find weekly_ad_url: on the same page
        item['weekly_ad_url'] = item['store_url'] = response.url
        zipcode = address.xpath(
            './/span[@class="postal-code"]/text()').extract()
        if len(zipcode):
            item['zipcode'] = zipcode[0]
        yield item

    def parse_hours(self, trs):
        trs = trs[1:]
        rows = [tr.xpath('td/text()') for tr in trs]

        if rows[0][0].extract() == self.hours_full_year:
            return get_hours_item_value([('12:00 a.m', '12:00 a.m') for _ in range(7)])
        else:
            sitedays = ['Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

            days = {}
            for row in rows:
                day_interval = row[0]
                time_interval = row[1].extract()

                day_idxes = None
                pieces = day_interval.re(r'(\w+) - (\w+)')
                if pieces:  # interval of days
                    day_idxes = range(
                        sitedays.index(pieces[0]), sitedays.index(pieces[1]) + 1)
                else:  # single day
                    d = day_interval.re(r'\w+')[0]
                    day_idxes = [sitedays.index(d)]

                if ' - ' in time_interval:
                    time_interval = time_interval.split(' - ')
                elif time_interval == 'Closed':
                    continue

                for i in day_idxes:
                    days[i] = time_interval
            return get_hours_item_value(days)
