import scrapy 
from scrapy.spiders import CrawlSpider
from scrapy.crawler import CrawlerProcess 
from scrapy import Request 
from itemloaders.processors import TakeFirst
from scrapy.loader import ItemLoader
from re import findall 
from math import ceil 
from scrapy.shell import inspect_response
from urllib.parse import quote 
from scrapy.utils.response import open_in_browser
import json 
from math import ceil 
from parsel import Selector 
from typing import List 
from scrapy.http.response.html import HtmlResponse


class DetailsItem(scrapy.Item):
    pass


class InfosSpider(scrapy.Spider):
    name = 'extractor'  
    body_template = '__LASTFOCUS=&__EVENTTARGET=&__EVENTARGUMENT=&__VIEWSTATE={viewstate}&__VIEWSTATEGENERATOR={view_gen}&__SCROLLPOSITIONX=0&__SCROLLPOSITIONY=0&__PREVIOUSPAGE={previous_page}&ctl00%24cphMainContent%24ddlProfesionalList=156&ctl00%24cphMainContent%24txtLicenseNumber1={license}&ctl00%24cphMainContent%24txtLicenseNumber2=&ctl00%24cphMainContent%24txtLicenseNumber3=&ctl00%24cphMainContent%24txtLicenseNumber4=&ctl00%24cphMainContent%24txtLicenseNumber5=&ctl00%24cphMainContent%24txtLicenseNumber6=&ctl00%24cphMainContent%24txtLicenseNumber7=&ctl00%24cphMainContent%24txtLicenseNumber8=&ctl00%24cphMainContent%24txtLicenseNumber9=&ctl00%24cphMainContent%24btnSearch=Search'
    headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://online.drl.wi.gov',
            'Referer': 'https://online.drl.wi.gov/LicenseLookup/MultipleCredentialSearch.aspx',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    data_fetching_template = 'https://online.drl.wi.gov/LicenseLookup/{}'

    def start_requests(self):
        yield Request(
            'https://online.drl.wi.gov/LicenseLookup/MultipleCredentialSearch.aspx',
        )

    def parse(self,response):
        for license in range(1000):
            values = self.get_values(response)
            yield Request(
                'https://online.drl.wi.gov/LicenseLookup/MulCredentialSearchResults.aspx',
                method='POST',
                headers=self.headers,
                dont_filter=True,
                body=self.body_template.format(
                    viewstate=quote(values[0]),
                    view_gen=quote(values[1]),
                    previous_page = quote(values[2]),
                    license=license
                ),
                callback=self.parse_listing,
            )

    def parse_listing(self,response):
        people_urls = response.xpath('//a[contains(@id,"CredentialSearchResults")]//@href').getall()
        for url in people_urls :
            yield Request(
                self.data_fetching_template.format(url),
                callback=self.parse_credential,
            )

    def parse_credential(self,response) :
        item = {
            sel.xpath('string(./td[1])').get().strip():sel.xpath('string(./td[2])').get().strip() 
            for  sel in self.get_relevant_tds(response)
        }
        orders_url = response.xpath('//a[contains(@id,"hlOrdersLink")]/@href').get()
        yield Request(
            self.data_fetching_template.format(orders_url),
            callback=self.parse_orders,
            meta={
                'item':item
            }
        )

    def parse_orders(self,response):
        item = response.meta['item']
        item.update(
            {
                'orders':[
                            {
                                'Hearing ID':sel.xpath('string(./td[1])').get().strip(),
                                'Order Date':sel.xpath('string(./td[2])').get().strip(),
                                'Subject':sel.xpath('string(./td[3])').get().strip()
                            }
                        for sel in response.xpath('//div[@id="CredSummaryDetails"]/table[last()]//tr[position()>2]')
                        ]
            }
        )
        yield item 

    def get_values(self,response:HtmlResponse) -> tuple :
        """
        This function extracts the values related to asp type site from a given `response` object.

        Args:
            response (HtmlResponse): The response object containing the HTML document to extract the values from.

        Returns:
            tuple: A tuple containing the extracted values of the '__VIEWSTATE', '__VIEWSTATEGENERATOR', and '__PREVIOUSPAGE' form fields.
        """
        viewstate = response.xpath('//input[@id="__VIEWSTATE"]/@value').get()
        viewstategen = response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').get()
        previous_page = response.xpath('//input[@id="__PREVIOUSPAGE"]/@value').get()
        return (
            viewstate,
            viewstategen,
            previous_page,
        )
    
    def get_relevant_tds(self,response) -> List[Selector] :
        """
        This function extracts a list of table rows containing two table cells (td) elements from a given `response` object.

        Args:
            response (HtmlResponse): The response object containing the HTML document to extract the rows from.

        Returns:
            List[Selector]: A list of `Selector` objects containing the relevant table rows.
        """
        return  response.xpath('//div[@id="CredSummaryDetails"]/table[position()=1 or position()=4]').xpath('.//tr[count(td)=2]')

process = CrawlerProcess(
    {
        #'LOG_LEVEL':'ERROR',
        'CONCURENT_REQUESTS':4,
        'DOWNLOAD_DELAY':0.5,
        #'HTTPCACHE_ENABLED' : True,
        'FEED_URI':'output.csv',
        'FEED_FORMAT':'csv',
    }
)
process.crawl(InfosSpider)
process.start()
