from scrapy.spider import Spider
from scrapy.http import Request, FormRequest
from scrapy.contrib.linkextractors import LinkExtractor

from bunch.items import ProductItem
from httplib2 import Response

from urlparse import urlparse, parse_qs

class HhgreggProductSpider(Spider):
    name = 'hhgregg'
    allowed_domains = ['www.hhgregg.com']
    start_urls0 = ['http://www.hhgregg.com/appliances-home',
                  'http://www.hhgregg.com/tv-entertainment',
                  'http://www.hhgregg.com/furniture-home',
                  'http://www.hhgregg.com/computers-mobile']
    
    start_urls = ['http://www.hhgregg.com/appliances-home']
    
    meta_level = 'hhgregg_product_spider_level'
    meta_page = 'hhgregg_product_spider_page'
    meta_brand = 'hhgregg_product_spider_brand'

    level_category_0 = 0
    level_category_1 = 1
    level_list = 2
    level_details = 3 
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, meta={self.meta_level: self.level_category_0}, dont_filter=True)

    def parse(self, response):
        if response.meta[self.meta_level] == self.level_category_0: #get links from category lovel 0
            for link in LinkExtractor(restrict_xpaths='//*[@id="left_nav"]//div[@class="widget_left_nav"][1]').extract_links(response)[:1]:
                yield Request(link.url, callback=self.parse, meta={self.meta_level: self.level_category_1})
        
        elif response.meta[self.meta_level] == self.level_category_1: #get links with brands from category lovel 1
            path = '//legend[contains(., "Brand")]/following-sibling::div'
            block = response.xpath(path)
            brands = [s.strip() for s in block.xpath('.//span[@class="spanacce"]/text()').extract()]
            for i, url in enumerate(block.xpath('.//a/@onclick').re(r"redirectToPLP\('([^']+)'\)")[:1]):
                yield Request(url, callback=self.parse, meta={self.meta_level: self.level_list, self.meta_brand: brands[i]})
        
        elif response.meta[self.meta_level] == self.level_list: #get links from product list
            brand = response.meta[self.meta_brand]
            for link in LinkExtractor(restrict_xpaths='//*[@class="product_listing_container"]//h3').extract_links(response)[:1]:
                yield Request(link.url, callback=self.parse, meta={self.meta_level: self.level_details, self.meta_brand: brand})
            
            #get next page of product list
            #page = response.meta[self.meta_page] + 1 if self.meta_page in response.meta else 2
            #if response.xpath('(//*[@class="pages center"])[1]//a[contains(.,%d)]' % page):
            #    yield self.get_page_request(response, page, {self.meta_level: self.level_list_page, self.meta_brand: brand})
            
        elif response.meta[self.meta_level] == self.level_details: #get product details
            item = ProductItem()
            details = response.xpath('//*[@id="prod_detail_main"]')[0]
            price_block = details.xpath('//*[@class="pricing"]')[0]
            currency, current_price = price_block.xpath('.//span[contains(.,"Your Price")]/following-sibling::span/text()')[0].re('\s*(\S)([\d,.]+)')
            item['currency'] = currency
            item['current_price'] = float(current_price.replace(',', ''))
            item['original_price'] = price_block.xpath('.//span[contains(.,"SRP")]/following-sibling::span/text()')[0].re('\s*\S([\d,.]+)')[0]
            
            xs = lambda node, x: node.xpath(x)[0].extract()
            
            item['description'] = xs(response, '//head/meta[@property="og:description"]/@content')
            item['brand'] = response.meta[self.meta_brand]
            item['title'] = xs(details, './/h1/text()')
            item['retailer_id'] = response.url.split('/').pop() #replace
            item['model'] = details.xpath('.//span[@class="model_no"]').re('Model: (\w+)')[0]
            specs = response.xpath('//*[@id="Specifications"]')[0]
            item['mpn'] = xs(specs, './/span[contains(.,"Manufacturer Model Number:")]/following-sibling::span/text()').strip()
            item['sku'] = response.xpath('//script/text()').re("var sku= '(\w+)';")[0]
            #todo: find upc
            #item['image_urls'] =
            item['primary_image_url'] = response.xpath('//head/meta[@property="og:image"]/@content')[0].extract()
            item['features'] = [''.join(span.xpath('.//text()').extract()) for span in response.xpath('//*[@class="features_list"]/ul/li/span')]
            item['specifications'] = self.get_specifications(specs, xs) 
            
            #trail: (string list) Ordered string array (highest level category first) of categories

            #rating: (string) Product rating normalized to 100 scale: 3.5/5 = 70
            
            #available_instore: (boolean) Is this product available in store?
            
            #available_online: (boolean) Is this product available for purchase online?
            yield item
            
    def get_specifications(self, specs, xs):
        s = {}
        counts = {} #for duplicate keys
        import pdb; pdb.set_trace()
        for div in specs.xpath('.//*[@class="specDetails"]/div'):
            key = div.xpath('span[1]//text()')[0].re('([^:]+):')[0]
            counts[key] = counts[key]+1 if key in counts else 1
            if counts[key] > 1:
                key = '%s (%d)' % (key, counts[key])
            s[key] = ''.join(xs(div, 'span[2]//text()')).strip()
        return s
        
    def get_page_request(self, response, page, meta):
        url = response.xpath('//body/script[1]').re(r"SearchBasedNavigationDisplayJS.init\('([^']+)'\);")[0]
        params = parse_qs(urlparse(url).query)
        formdata = {'contentBeginIndex':0,
                    'productBeginIndex': (page-1)*12,
                    'beginIndex': (page-1)*12,
                    'orderBy':6,
                    'isHistory':'false',
                    'pageView':'image',
                    'resultType':'products',
                    'orderByContent':'',
                    'searchTerm':'',
                    'facet':'',
                    'minPrice':'',
                    'maxPrice':'',
                    'resultsPerPage':'',
                    'storeId':params['storeId'][0],
                    'catalogId':params['catalogId'][0],
                    'langId':-1,
                    'NUMITEMSINCART':' item(s)',
                    'objectId':'',
                    'requesttype':'ajax' }
        return FormRequest(url, callback=self.parse, formdata=formdata, meta=meta, headers={'X-Requested-With':'XMLHttpRequest'})