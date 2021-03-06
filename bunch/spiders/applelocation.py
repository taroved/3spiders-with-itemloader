from scrapy.contrib.spiders import CrawlSpider
from scrapy.http import Request
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.contrib.loader.processor import TakeFirst

from bunch.items import LocationLoader


class AppleLocationSpider(CrawlSpider):
    name = 'apple'
    allowed_domains = ['www.apple.com']
    start_urls = ['http://www.apple.com/retail/storelist/']

    meta_country = 'apple_location_spider_country'

    hours_countries = ['United States']
    hours_full_year = '24/7, 365 days a year'

    def parse_start_url(self, response):
        """Parse start page with links.        
        (The docstring contains scrapy contracts.
        Read more at http://doc.scrapy.org/en/latest/topics/contracts.html )

        @url http://www.apple.com/retail/storelist/
        @returns requests 447
        """
        for menuitem in response.xpath('//section[@id="country_switcher"]/div/ul/li'):
            code = menuitem.xpath('@data-tag')[0].extract()
            name = menuitem.xpath('text()')[0].extract()
            path = '//div[@id="%s"]/div/ul/li/a' % (code + 'stores')
            for link in LinkExtractor(restrict_xpaths=path).extract_links(response):
                yield Request(link.url, callback=self.parse_store, meta={self.meta_country: name})

    def parse_store(self, response):
        """Scraping of items.

        @url http://www.apple.com/retail/thesummit/
        @returns items 1 1
        @scrapes address phone_number services state store_image_url store_name store_id store_url weekly_ad_url zipcode
        """
        il = LocationLoader(response=response)
        il.selector = response.xpath('(//address)[1]')

        il.add_xpath('city', './/span[@class="locality"]/text()')
        il.add_xpath('address', 'div[@class="street-address"]/text()',
                     lambda x: [s.strip() for s in x])
        if self.meta_country in response.meta:
            il.add_value('country', response.meta[self.meta_country])
            if il.get_collected_values('country')[0] in self.hours_countries:
                il.add_value('hours',
                             il.selector.xpath(
                                 '../table[@class="store-info"][1]/tr'),
                             self.parse_hours)
        il.add_xpath('phone_number', 'div[@class="telephone-number"]/text()',
                     TakeFirst(), unicode.strip)
        il.add_xpath('services',
                     '//nav[@class="nav hero-nav selfclear"]//img/@alt')
        il.add_xpath('state', './/span[@class="region"]/text()', TakeFirst())
        # store_email: not found
        # store_floor_plan_url: not found
        il.add_xpath('store_image_url',
                     '../../div[@class="column last"]/img/@src',
                     TakeFirst())
        il.add_xpath('store_name', 'div[@class="store-name"]/text()',
                     TakeFirst(), unicode.strip)
        il.add_xpath('store_id', '/html/head/meta[@name="omni_page"]/@content',
                     TakeFirst(), re=r'(R\d+)$')
        # find weekly_ad_url: on the same page
        il.add_value('weekly_ad_url', response.url)
        il.add_value('store_url', response.url)
        il.add_xpath('zipcode', './/span[@class="postal-code"]/text()',
                     TakeFirst())

        yield il.load_item()

    def parse_hours(self, trs):
        trs = trs[1:]
        rows = [tr.xpath('td/text()') for tr in trs]

        if rows[0][0].extract() == self.hours_full_year:
            return [('12:00 a.m', '12:00 a.m') for _ in range(7)]
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
            return days
