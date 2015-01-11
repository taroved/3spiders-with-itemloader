from urlparse import urlparse, parse_qsl

from scrapy import Spider
from scrapy.http import Request, FormRequest
from scrapy.selector import Selector
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.contrib.loader import ItemLoader
from scrapy.contrib.loader.processor import TakeFirst, Identity, MapCompose

from bunch.items import ProductItem


class HhgreggProductSpider(Spider):
    name = 'hhgregg'
    allowed_domains = ['www.hhgregg.com',
                       'hhgregg.scene7.com']
    start_urls = ['http://www.hhgregg.com/appliances-home',
                  'http://www.hhgregg.com/tv-entertainment',
                  'http://www.hhgregg.com/furniture-home',
                  'http://www.hhgregg.com/computers-mobile']

    meta_subcategory = 'hhgregg_product_spider_subcategory'
    meta_page = 'hhgregg_product_spider_page'
    meta_page_url = 'hhgregg_product_spider_page_url'
    meta_url_stack = 'hhgregg_product_spider_url_stack'  # for debug
    meta_itemloader = 'hhgregg_product_spider_item'

    image_url_pattern = "http://hhgregg.scene7.com/is/image/hhgregg/%s"

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        """Parse links from category and subcategory.

        @url http://www.hhgregg.com/appliances-home
        @returns requests 9
        """
        for link in LinkExtractor(restrict_xpaths='//*[@id="left_nav"]//div[@class="widget_left_nav"][1]').extract_links(response):
            if self.meta_subcategory in response.meta:
                yield Request(link.url, callback=self.parse_list,
                              meta={self.meta_url_stack: self.stack_push(response, link.url)})
            else:
                yield Request(link.url, callback=self.parse_category,
                              meta={
                                  self.meta_subcategory: True,
                                  self.meta_url_stack: self.stack_push(response, link.url)})

    def parse_list(self, response):
        """Parse product links from product list and return next page request.

        @url http://www.hhgregg.com/appliances-home/refrigerators
        @returns requests 13 13
        """
        # get product details requests
        for link in LinkExtractor(
            restrict_xpaths='//*[@class="product_listing_container"]//h3',
            allow='/item/'
        ).extract_links(response):
            yield Request(link.url, callback=self.parse_details,
                          meta={'dont_redirect': True,
                                self.meta_url_stack: self.stack_push(response, link.url)})

        # get next page of product list
        if self.meta_page in response.meta:
            page = response.meta[self.meta_page] + 1
            url = response.meta[self.meta_page_url]
        else:
            page = 2
            # we can get the url only in non-ajax response
            url = response.xpath(
                '//body/script[1]').re(r"SearchBasedNavigationDisplayJS.init\('([^']+)'\);")[0]
        if response.xpath('(//*[@class="pages center"])[1]//a[contains(.,%d)]' % page):
            yield self.get_page_request(page,
                                        {
                                            self.meta_page: page,
                                            self.meta_page_url: url,
                                            self.meta_url_stack: self.stack_push(response, (page, url))
                                        })

    def parse_details(self, response):
        """Parse product details into scrapy item.

        @url http://www.hhgregg.com/whirlpool-24-5-cu-ft-stainless-steel-french-door-4-door-refrigerator/item/WRX735SDBM
        @returns requests 1 1
        """
        il = ItemLoader(item=ProductItem(), response=response)
        details = response.xpath('//*[@id="prod_detail_main"]')[0]
        price_block = details.xpath('//*[@class="pricing"]')

        il.selector = price_block
        x = './/span[contains(.,"Your Price")]/following-sibling::span/text()'
        price_re = r'\s*\S([\d,.]+)'
        cur_re = r'\s*(\S)[\d,.]+'
        il.add_xpath('current_price', x, re=price_re)
        il.add_xpath('currency', x, re=cur_re)
        x = './/span[contains(.,"SRP")]/following-sibling::span/text()'
        il.add_xpath('original_price', x, re=price_re)
        il.add_xpath('currency', x, re=cur_re)

        il.selector = Selector(response)
        il.add_xpath('description',
                     '//head/meta[@property="og:description"]/@content')
        il.add_xpath('brand', '//script/text()', re="'entity.brand=([^']+)',")
        il.selector = details
        il.add_xpath('title', './/h1/text()')
        il.add_value('retailer_id', response.url.split('/').pop())
        il.add_xpath('model', './/span[@class="model_no"]', re=r'Model: (\w+)')
        # mpn: Manufacturer's Product Number. What is it? Where is it?
        il.selector = Selector(response)
        il.add_xpath('sku', '//script/text()', re="var sku= '([^']+)';")
        sku = il.get_collected_values('sku')[0]
        # upc: not found
        il.add_value('primary_image_url', self.image_url_pattern % sku)
        il.selector = Selector(response)
        il.add_value('features',
                     response.xpath('//*[@class="features_list"]/ul/li/span'),
                     MapCompose(lambda x: ''.join(x.xpath('.//text()').extract())))

        il.add_value('specifications', self.get_specifications(response))
        specs = il.get_collected_values('specifications')[0]
        il.add_value('mpn', specs.get('Manufacturer Model Number'))

        il.add_xpath('trail', '//*[@id="breadcrumb"]/a/text()',
                     lambda xl: xl[1:])

        il.add_xpath('rating', '//script/text()',
                     lambda x: int(float(x[0]) * 100 / 5),
                     re=r"'entity.ratingUrl=([\d.]+)',")

        discontinued = response.xpath(
            '//*[@class="available_soon_text2" and contains(.,"DISCONTINUED")]')
        if discontinued:
            # another availability cases depend on zip code
            il.add_value('available_instore', False)
            il.add_value('available_online', False)

        # now we have got all details except image_urls
        images_xml_url = self.image_url_pattern % sku + '?req=set,xml,UTF-8'
        yield Request(images_xml_url, callback=self.parse_images,
                      meta={self.meta_itemloader: il,
                            self.meta_url_stack: self.stack_push(response, images_xml_url)
                            })

    def parse_images(self, response):
        """Parse image_urls for item"""
        il = response.meta[self.meta_itemloader]
        img_ids = response.xpath('/set/item/s/@n').re('^hhgregg/(.+)$')
        for id in img_ids:
            il.add_value('image_urls', self.image_url_pattern % id)

        #  output processors
        il.default_output_processor = TakeFirst()
        il.features_out = Identity()
        il.image_urls_out = Identity()
        il.specifications_out = Identity()
        il.trail_out = Identity()

        yield il.load_item()

    def get_specifications(self, response):
        s = {}
        counts = {}  # for duplicate keys
        for div in response.xpath('//*[@id="Specifications"]//*[@class="specDetails"]/div'):
            key = div.xpath(
                '(span[1]/span | span[1])/text()')[0].re('([^:]+):?')[0]

            counts[key] = counts[key] + 1 if key in counts else 1
            if counts[key] > 1:
                key = '%s (%d)' % (key, counts[key])

            s[key] = ''.join(div.xpath('span[2]//text()').extract()).strip()
        return s

    def get_page_request(self, page, meta):
        """Return request for the page number"""
        url = meta[self.meta_page_url]

        params = parse_qsl(urlparse(url).query)
        params = {k: v for k, v in params}

        formdata = parse_qsl(
            "contentBeginIndex=0&productBeginIndex=12&beginIndex=12&orderBy=6&isHistory=false&pageView=image&resultType=products&orderByContent=&searchTerm=&facet=&minPrice=&maxPrice=&resultsPerPage=&storeId=10154&catalogId=10051&langId=-1&NUMITEMSINCART=%20item(s)&objectId=&requesttype=ajax")
        formdata = {k: v for k, v in formdata}
        formdata['productBeginIndex'] = formdata[
            'beginIndex'] = str((page - 1) * 12)
        formdata['storeId'] = params['storeId']
        formdata['catalogId'] = params['catalogId']

        return FormRequest(url, callback=self.parse_list, formdata=formdata,
                           meta=meta, headers={'X-Requested-With': 'XMLHttpRequest'})

    def stack_push(self, response, url):
        """Push url to urls stack in meta.
        Usable for debug. Helps to find page with broken links.
        """
        stack = response.meta[self.meta_url_stack][
            :] if self.meta_url_stack in response.meta else []
        stack.append(url)
        return stack
