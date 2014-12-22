from scrapy.spider import Spider
from scrapy.http import Request, FormRequest
from scrapy.contrib.linkextractors import LinkExtractor

from bunch.items import ProductItem
from httplib2 import Response

from urlparse import urlparse, parse_qsl

class HhgreggProductSpider(Spider):
    name = 'hhgregg'
    allowed_domains = ['www.hhgregg.com',
                       'hhgregg.scene7.com']
    start_urls = ['http://www.hhgregg.com/appliances-home',
                  'http://www.hhgregg.com/tv-entertainment',
                  'http://www.hhgregg.com/furniture-home',
                  'http://www.hhgregg.com/computers-mobile']
    
    meta_level = 'hhgregg_product_spider_level'
    meta_page = 'hhgregg_product_spider_page'
    meta_page_url = 'hhgregg_product_spider_page_url'
    meta_url_stack = 'hhgregg_product_spider_url_stack'
    meta_item = 'hhgregg_product_spider_item'

    level_category_0 = 0
    level_category_1 = 1
    level_list = 2
    level_details = 3
    level_images = 4
    
    image_url_pattern = "http://hhgregg.scene7.com/is/image/hhgregg/%s" 
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, meta={self.meta_level: self.level_category_0}, dont_filter=True)
    
    #usable for debug
    def stack_push(self, response, url):
        stack = [x for x in response.meta[self.meta_url_stack]] if self.meta_url_stack in response.meta else []
        stack.append(url)
        return stack
    
    def parse(self, response):
        if response.meta[self.meta_level] in (self.level_category_0, self.level_category_1): #get links from category level 0 and 1
            for link in LinkExtractor(restrict_xpaths='//*[@id="left_nav"]//div[@class="widget_left_nav"][1]').extract_links(response):#[:1]
                level = self.level_category_1 if response.meta[self.meta_level] == self.level_category_0 else self.level_list
                yield Request(link.url, callback=self.parse, meta={self.meta_level: level, self.meta_url_stack: self.stack_push(response, link.url)})

        elif response.meta[self.meta_level] == self.level_list: #get links from product list and turn the page
            #get product details requests
            for link in LinkExtractor(restrict_xpaths='//*[@class="product_listing_container"]//h3', allow='/item/').extract_links(response):
                yield Request(link.url, callback=self.parse, meta={self.meta_level: self.level_details, self.meta_url_stack: self.stack_push(response, link.url)})
            
            #get next page of product list
            if self.meta_page in response.meta:
                page = response.meta[self.meta_page] + 1
                url = response.meta[self.meta_page_url]
            else:
                page = 2
                url = response.xpath('//body/script[1]').re(r"SearchBasedNavigationDisplayJS.init\('([^']+)'\);")[0] #we can get the url only in non-ajax response
            if response.xpath('(//*[@class="pages center"])[1]//a[contains(.,%d)]' % page):
                yield self.get_page_request(response, page, {self.meta_level: self.level_list, self.meta_page: page, self.meta_page_url: url, self.meta_url_stack: self.stack_push(response, (page, url))})
            
        elif response.meta[self.meta_level] == self.level_details: #get product details
            item = ProductItem()
            details = response.xpath('//*[@id="prod_detail_main"]')[0]
            price_block = details.xpath('//*[@class="pricing"]')
            if price_block:
                price = price_block[0].xpath('.//span[contains(.,"Your Price")]/following-sibling::span/text()')
                if price:
                    item['currency'], current_price = price[0].re('\s*(\S)([\d,.]+)')
                    item['current_price'] = float(current_price.replace(',', ''))
                price = price_block[0].xpath('.//span[contains(.,"SRP")]/following-sibling::span/text()')
                if price:
                    item['currency'], original_price = price[0].re('\s*(\S)([\d,.]+)') 
                    item['original_price'] = original_price
            
            xs = lambda node, x: node.xpath(x)[0].extract()
            
            desc = response.xpath('//head/meta[@property="og:description"]/@content')
            if desc:
                item['description'] = desc[0].extract()
            item['brand'] = response.xpath('//script/text()').re("'entity.brand=([^']+)',")[0]
            item['title'] = xs(details, './/h1/text()')
            item['retailer_id'] = response.url.split('/').pop() #replace
            item['model'] = details.xpath('.//span[@class="model_no"]').re('Model: (\w+)')[0]
            #mpn: Manufacturer's Product Number. What is it? Where is it?
            item['sku'] = response.xpath('//script/text()').re("var sku= '([^']+)';")[0]
            #upc: not found
            #todo: item['image_urls'] = 
            item['primary_image_url'] = self.image_url_pattern % item['sku']
            item['features'] = [''.join(span.xpath('.//text()').extract()) for span in response.xpath('//*[@class="features_list"]/ul/li/span')]
            
            item['specifications'] = self.get_specifications(response)
            
            mpn_key = 'Manufacturer Model Number'
            if mpn_key in item['specifications']:
                item['mpn'] = item['specifications'][mpn_key]
            
            item['trail'] = response.xpath('//*[@id="breadcrumb"]/a/text()')[1:].extract()
            
            rating = lambda x: str(int(float(x)*100/5)) #the string type is in the task
            item['rating'] = rating(response.xpath('//script/text()').re("'entity.ratingUrl=([\d.]+)',")[0])
            
            discontinued = response.xpath('//*[@class="available_soon_text2" and contains(.,"DISCONTINUED")]')
            if discontinued:
                #another availability cases depend on zip code
                item['available_instore'] = item['available_online'] = False
            
            #now we have got all details except image_urls
            images_xml_url = self.image_url_pattern % item['sku'] + '?req=set,xml,UTF-8' 
            yield Request(images_xml_url, callback=self.parse, meta={self.meta_level: self.level_images, self.meta_item: item, self.meta_url_stack: self.stack_push(response, images_xml_url)})
        
        elif response.meta[self.meta_level] == self.level_images: #additional level. We need it to get image_urls
            item = response.meta[self.meta_item]
            img_ids = response.xpath('/set/item/s/@n').re('^hhgregg/(.+)$')
            item['image_urls'] = [self.image_url_pattern % id for id in img_ids]
            yield item
            
    def get_specifications(self, response):
        s = {}
        counts = {} #for duplicate keys
        for div in response.xpath('//*[@id="Specifications"]//*[@class="specDetails"]/div'):
            key = div.xpath('(span[1]/span | span[1])/text()')[0].re('([^:]+):?')[0]

            counts[key] = counts[key]+1 if key in counts else 1
            if counts[key] > 1:
                key = '%s (%d)' % (key, counts[key])
            
            s[key] = ''.join(div.xpath('span[2]//text()').extract()).strip()
        return s
        
    def get_page_request(self, response, page, meta):
        url = meta[self.meta_page_url]
        
        params = parse_qsl(urlparse(url).query)
        params = {k:v for k,v in params}
        
        formdata = parse_qsl("contentBeginIndex=0&productBeginIndex=12&beginIndex=12&orderBy=6&isHistory=false&pageView=image&resultType=products&orderByContent=&searchTerm=&facet=&minPrice=&maxPrice=&resultsPerPage=&storeId=10154&catalogId=10051&langId=-1&NUMITEMSINCART=%20item(s)&objectId=&requesttype=ajax")
        formdata = {k:v for k,v in formdata}
        formdata['productBeginIndex'] = formdata['beginIndex'] = str((page-1)*12)
        formdata['storeId'] = params['storeId']
        formdata['catalogId'] = params['catalogId']
        
        return FormRequest(url, callback=self.parse, formdata=formdata, meta=meta, headers={'X-Requested-With':'XMLHttpRequest'})