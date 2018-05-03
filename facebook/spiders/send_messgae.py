# -*- coding: utf-8 -*-
import re
import time

import scrapy
import redis


class SeedMessageSpider(scrapy.Spider):
    name = 'send_message'
    download_delay = 60
    username = '15601202268'
    # allowed_domains = ['www.facebook.com']
    start_urls = [
        'https://www.facebook.com/jf.luo.5',
    ]
    proxies = {
        'http': 'socks5h://127.0.0.1:1080',
        'https': 'socks5h://127.0.0.1:1080',
    }
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    custom_settings = {
        'ITEM_PIPELINES': {
            'facebook.pipelines.FriendsPipeline': 100,
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
        user_id = re.findall(r'content="fb://profile/(\d+)"', response.text)[0]
        url = 'https://m.facebook.com/messages/read/?fbid={}&_rdr'.format(user_id)
        headers = {
            'authority': 'www.facebook.com',
            'method': 'GET',
            'scheme': 'https',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
        }
        meta = {'proxy': self.proxies['https'], 'user_id': user_id}
        yield scrapy.FormRequest(url, method='GET', headers=headers, meta=meta,
                                 cookies=self._get_cookie(), callback=self.parse_send_message)

    def parse_send_message(self, response):
        url = 'https://m.facebook.com/messages/send/?icm=1&refid=12'
        headers = {
            'authority': 'm.facebook.com',
            'method': 'POST',
            'scheme': 'https',
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://m.facebook.com',
            'pragma': 'no-cache',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Mobile Safari/537.36',
            'x-msgr-region': 'ATN',
            'x-requested-with': 'XMLHttpRequest',
            'x-response-format': 'JSONStream',
        }
        user_id = response.meta['user_id']
        fb_dtsg = response.xpath(r'//input[@name="fb_dtsg"]/@value').extract_first()
        tids = response.xpath(r'//input[@name="tids"]/@value').extract_first()
        wwwupp = response.xpath(r'//input[@name="wwwupp"]/@value').extract_first()
        # tmp = response.xpath(r'//input[@name="ids\[{}\]"]/@value'.format(user_id)).extract_first()
        ajax = re.findall(r'"encrypted":"(.*?)"', response.text)[0]
        cookie = self._get_cookie()
        data = {
            'tids': tids,
            'wwwupp': wwwupp,
            'ids[{}]'.format(user_id): user_id,
            'body': 'hello',
            'waterfall_source': 'message',
            'action_time': str(int(time.time()*1000)),
            'm_sess': '',
            'fb_dtsg': fb_dtsg,
            '__dyn': '',
            '__req': '27',
            '__ajax__': ajax,
            '__user': cookie['c_user'],
        }
        meta = {'proxy': self.proxies['https']}
        yield scrapy.FormRequest(url, method='POST', headers=headers, formdata=data, meta=meta, cookies=cookie, callback=self.parse_send)

    def parse_send(self, response):
        pass

    def _get_cookie(self):
        cookie = self.redis_client.get('cookie:facebook:{}'.format(self.username))
        if not cookie:
            raise ValueError('user not found')
        return eval(cookie)
