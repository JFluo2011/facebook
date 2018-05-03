# -*- coding: utf-8 -*-
import re
import json

import demjson
import scrapy
import redis
from lxml import etree

from facebook.items import FriendsItem


class FriendsRelationSpider(scrapy.Spider):
    name = 'friends_relation'
    download_delay = 60
    username = '13087747934'
    allowed_domains = ['www.facebook.com']
    start_urls = [
        # 'https://www.facebook.com/park.yukki.98',
        # 'https://www.facebook.com/profile.php?id=100023820229714',
        'https://www.facebook.com/kim.amorinha',
        # 'https://www.facebook.com/lydia.dong',
        # 'https://www.facebook.com/joe.shaw.1806',
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
            if 'profile.php' in url:
                url_friends = url + '&sk=friends'
                # url_following = url + '&sk=following'
            else:
                url_friends = url + '/friends'
                # url_following = url + '/following'
            yield scrapy.Request(url_friends, method='GET', headers=headers, meta=meta,
                                 cookies=self._get_cookie(), callback=self.parse_friends)
            # yield scrapy.Request(url_following, method='GET', headers=headers, meta=meta,
            #                      cookies=self._get_cookie(), callback=self.parse_following)

    def parse_following(self, response):
        if 'friend_list_item' not in response.text:
            print('permissions issue')
            return
        user_id = re.findall(r'content="fb://profile/(\d+)"', response.text)[0]
        yield self._parse_following_homepage(response, user_id)
        if 'fbProfileBrowserNoMoreItems' in response.text:
            print('no more following page')
            return
        cookie = self._get_cookie()
        url = 'https://www.facebook.com/ajax/browser/list/following_user/'
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
        regex = r'/browser/list/following_user/\?profile_id=(\d+)&amp;context=(.*?)&amp;timestamp=(\d+)&amp;start=(\d+)'
        profile_id, context, timestamp, start = re.findall(regex, response.text)[0]
        params = {
            'profile_id': profile_id,
            'context': context,
            'timestamp': timestamp,
            'start': start,
            'dpr': '1',
            '__user': cookie['c_user'],
            '__a': '1',
            '__dyn': '',
            '__req': 'm',
            '__be': '1',
            '__pc': re.findall(r'"pkg_cohort":"(.*?)"', response.text)[0],
            '__rev': re.findall(r'"__spin_r":(.*?),', response.text)[0],
            '__spin_r': re.findall(r'"__spin_r":(.*?),', response.text)[0],
            '__spin_b': re.findall(r'"__spin_b":"(.*?)",', response.text)[0],
            '__spin_t': re.findall(r'"__spin_t":(.*?),', response.text)[0],
        }
        meta = {'params': params, 'start': int(start), 'user_id': user_id, 'proxy': self.proxies['https']}
        yield scrapy.FormRequest(url, method='GET', formdata=params, headers=headers, meta=meta,
                                 cookies=cookie, callback=self.parse_following_next_page)

    def parse_following_next_page(self, response):
        user_id = response.meta['user_id']
        yield self._parse_following_homepage(response, user_id)

        if 'fbProfileBrowserNoMoreItems' in response.text:
            print('no more following page')
            return
        # next page
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
        start = response.meta['start'] + 10
        params.update({'start': str(start)})
        meta = {'params': params, 'user_id': user_id, 'start': start, 'proxy': self.proxies['https']}
        cookie = self._get_cookie()
        params.update({'__user': cookie['c_user']})
        url = 'https://www.facebook.com/ajax/browser/list/following_user/'
        yield scrapy.FormRequest(url, method='GET', formdata=params, headers=headers, meta=meta,
                                 cookies=cookie, callback=self.parse_following_next_page)

    def _parse_following_homepage(self, response, user_id):
        lst = []
        if response.meta.get('first_page', False):
            selector = etree.HTML(
                re.findall(r'<!-- (<ul class=.*?data-testid="friend_list_item".*?) --></code>', response.text)[0])
            if selector is not None:
                lst.extend(selector.xpath(r'//div[@data-testid="friend_list_item"]/a/@href'))
        else:
            source = re.findall(r'"__html":"(<div class=".*?/div>)"',
                                response.text.encode('utf-8').decode('unicode_escape'))[0]
            selector = etree.HTML(source)
            if selector is not None:
                lst = selector.xpath(r'//div[@data-testid="friend_list_item"]/a/@href')

        item = FriendsItem()
        friend_lst = [(url.split('?')[0] if 'profile.php' not in url else url.split('&')[0]) for url in lst]
        item['user_id'] = user_id
        item['type_'] = 'following'
        item['friends_lst'] = friend_lst
        return item

    def parse_friends(self, response):
        if 'friend_list_item' not in response.text:
            print('permissions issue')
            return
        user_id = re.findall(r'content="fb://profile/(\d+)"', response.text)[0]
        yield self._get_friends_homepages(response, user_id)

        # next page
        params = self._parse_params(response)
        if params is None:
            print('no more friends page')
            return
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
        url = 'https://www.facebook.com/ajax/pagelet/generic.php/AllFriendsAppCollectionPagelet'
        cookie = self._get_cookie()
        params.update({'__user': cookie['c_user']})
        meta = {'params': params, 'user_id': user_id, 'proxy': self.proxies['https']}
        yield scrapy.FormRequest(url, method='GET', formdata=params, headers=headers, meta=meta,
                                 cookies=cookie, callback=self.parse_next_page)

    def parse_next_page(self, response):
        user_id = response.meta['user_id']
        yield self._get_friends_homepages(response, user_id)

        # next page
        # if 'disablepager' not in response.text:
        #     print('no more friends page')
        #     return
        try:
            cursor = re.findall(r'\["pagelet_timeline_app_collection_.*?",{.*?},"(.*?)"\]\],', response.text)[0]
        except:
            print('no more friends page')
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
        data.update({'cursor': cursor})
        params.update({'data': json.dumps(data, separators=(',', ':'))})
        meta = {'params': params, 'user_id': user_id, 'proxy': self.proxies['https']}
        cookie = self._get_cookie()
        params.update({'__user': cookie['c_user']})
        url = 'https://www.facebook.com/ajax/pagelet/generic.php/AllFriendsAppCollectionPagelet'
        yield scrapy.FormRequest(url, method='GET', formdata=params, headers=headers, meta=meta,
                                 cookies=cookie, callback=self.parse_next_page)

    def _get_friends_homepages(self, response, user_id):
        lst = []
        if response.meta.get('first_page', False):
            res = re.findall(r'<!-- (<div class=.*?data-testid="friend_list_item".*?) --></code>', response.text)
            if res:
                selector = etree.HTML(res[0])
                lst.extend(selector.xpath(r'//div[@data-testid="friend_list_item"]/a/@href'))
        else:
            json_data = json.loads(response.text[response.text.find('{'):])
            selector = etree.HTML(json_data.get('payload', ''))
            if selector is not None:
                lst = selector.xpath(r'//div[@data-testid="friend_list_item"]/a/@href')

        item = FriendsItem()
        friend_lst = [(url.split('?')[0] if 'profile.php' not in url else url.split('&')[0]) for url in lst]
        item['user_id'] = user_id
        item['type_'] = 'friend'
        item['friends_lst'] = friend_lst
        return item

    def _get_cookie(self):
        cookie = self.redis_client.get('cookie:facebook:{}'.format(self.username))
        if not cookie:
            raise ValueError('user not found')
        return eval(cookie)

    def _parse_params(self, response):
        try:
            data = demjson.decode(re.findall(r'\[({disablepager:.*?})\]\],', response.text)[0])
            collection_token, cursor = re.findall(r'\["pagelet_timeline_app_collection_(\d+:\d+:\d+)",{.*?},"(.*?)"\]\],',
                                                  response.text)[0]
            data.update({
                'collection_token': collection_token,
                'cursor': cursor,
                'ftid': None,
                'order': None,
                'sk': 'friends',
                'importer_state': None,
            })
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
