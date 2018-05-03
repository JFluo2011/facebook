# -*- coding: utf-8 -*-
import re
import json

import demjson
import scrapy
import redis
from lxml import etree

from facebook.items import PublicPageItem


class PublicPageSpider(scrapy.Spider):
    name = 'public_page'
    download_delay = 60
    username = '13087747934'
    allowed_domains = ['www.facebook.com']
    search_key = 'trump donald'
    start_urls = [
        'https://www.facebook.com/search/pages/?q={}'.format(search_key)
    ]
    proxies = {
        'http': 'socks5h://127.0.0.1:1080',
        'https': 'socks5h://127.0.0.1:1080',
    }
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    custom_settings = {
        'ITEM_PIPELINES': {
            'facebook.pipelines.PublicPagePipeline': 100,
        },
    }

    def start_requests(self):
        headers = {
            'authority': 'www.facebook.com',
            'method': 'GET',
            'scheme': 'https',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
        }
        meta = {
            'proxy': self.proxies['https'],
            'first_page': True,
        }
        for url in self.start_urls:
            yield scrapy.Request(url, method='GET', headers=headers, meta=meta, cookies=self._get_cookie())

    def parse(self, response):
        if 'EntOwnedPage' not in response.text:
            print('{}: search failed'.format(self.search_key))
            return
        for item in self.parse_item(response):
            yield item

        # next page
        params = self._parse_params(response)
        if params is None:
            print('no more page')
            return
        headers = {
            'authority': 'www.facebook.com',
            'method': 'GET',
            'scheme': 'https',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
        }
        url = 'https://www.facebook.com/ajax/pagelet/generic.php/BrowseScrollingSetPagelet'
        cookie = self._get_cookie()
        params.update({'__user': cookie['c_user']})
        meta = {'params': params, 'proxy': self.proxies['https']}
        yield scrapy.FormRequest(url, method='GET', formdata=params, headers=headers, meta=meta,
                                 cookies=cookie, callback=self.parse_next_page)

    def parse_next_page(self, response):
        for item in self.parse_item(response):
            yield item

        # next page
        try:
            cursor, page_number = re.findall(r'\[{"cursor":"(.*?)","page_number":(\d+),', response.text)[0]
        except:
            print('no more page')
            return

        headers = {
            'authority': 'www.facebook.com',
            'method': 'GET',
            'scheme': 'https',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
        }
        params = response.meta['params']
        data = json.loads(params['data'])
        data.update({'cursor': cursor, 'page_number': int(page_number)})
        params.update({'data': json.dumps(data, separators=(',', ':'))})
        meta = {'params': params, 'proxy': self.proxies['https']}
        cookie = self._get_cookie()
        params.update({'__user': cookie['c_user']})
        url = 'https://www.facebook.com/ajax/pagelet/generic.php/BrowseScrollingSetPagelet'
        yield scrapy.FormRequest(url, method='GET', formdata=params, headers=headers, meta=meta,
                                 cookies=cookie, callback=self.parse_next_page)

    def parse_item(self, response):
        text = ''
        if response.meta.get('first_page', False):
            regex = (r'bigPipe.beforePageletArrive\("pagelet_dock"\).*?'
                     r'<!-- (<div data-bt=".*?id="BrowseResultsContainer".*?EntOwnedPage.*?'
                     r'</iframe></div></div></div></div></div>) --></code>')
            result = re.findall(regex, response.text, re.DOTALL)
            if result:
                text = result[0]
            regex = (r'bigPipe.beforePageletArrive\("fbRequestsList_wrapper"\).*?'
                     r'<!-- (<div class=".*?data-testid="results".*?EntOwnedPage.*?'
                     r'</iframe></div></div></div></div>) --></code>')
            result = re.findall(regex, response.text, re.DOTALL)
            if result:
                text += result[0]
        else:
            json_data = json.loads(response.text[response.text.find('{'):])
            text = json_data.get('payload', '')
        if text == '':
            return
        selector = etree.HTML(text)
        for sel in selector.xpath(r'//div[@class="clearfix"]'):
            item = PublicPageItem()
            item['home'] = selector.xpath('.//a[@class="_32mo"]/@href')[0].split('?')[0]
            item['nick_name'] = selector.xpath('.//a[@class="_32mo"]/span/text()')[0]
            item['portrait'] = selector.xpath(r'//img[contains(@class, "_1glk img")]/@src')[0]
            item['account_name'] = item['home'].split('/')[-2]
            item['introduce'] = sel.xpath(r'.//div[@class="_52eh _5bcu"]')[1].xpath('string(.)')
            try:
                item['type'] = sel.xpath(r'.//div[@class="_pac"]/a[2]/text()')[0]
            except:
                item['type'] = sel.xpath(r'.//div[@class="_pac"]/span[2]/text()')[0]

            yield item

    def _get_cookie(self):
        cookie = self.redis_client.get('cookie:facebook:{}'.format(self.username))
        if not cookie:
            raise ValueError('user not found')
        return eval(cookie)

    def _parse_params(self, response):
        try:
            data = demjson.decode(re.findall(r'({view:.*?filter_ids.*?}),null', response.text)[0])
            data.update(demjson.decode(re.findall(r'\[({cursor:.*?page_number.*?})\]', response.text)[0]))
        except:
            print('no another page')
            return None
        params = {
            'dpr': '1',
            'data': json.dumps(data, separators=(',', ':')),
            '__a': '1',
            '__dyn': '',
            '__req': 'u',
            '__be': '1',
            '__pc': re.findall(r'"pkg_cohort":"(.*?)"', response.text)[0],
            '__rev': re.findall(r'"__spin_r":(.*?),', response.text)[0],
            '__spin_r': re.findall(r'"__spin_r":(.*?),', response.text)[0],
            '__spin_b': re.findall(r'"__spin_b":"(.*?)",', response.text)[0],
            '__spin_t': re.findall(r'"__spin_t":(.*?),', response.text)[0],
        }
        return params
