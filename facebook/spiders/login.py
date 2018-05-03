import time
import re
import traceback

import redis
import arrow
import requests
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()


def get_cookie(username, password):
    session = requests.session()
    url = 'https://m.facebook.com/?refsrc=https%3A%2F%2Fwww.facebook.com%2F&_rdr'
    headers = {
        'Host': 'm.facebook.com',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    }
    resp = session.get(url, headers=headers, verify=False)
    soup = BeautifulSoup(resp.text, 'html.parser')

    try:
        url = 'https://m.facebook.com/login/async/?refsrc=https%3A%2F%2Fwww.facebook.com'
        headers = {
            'Host': 'm.facebook.com',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://m.facebook.com',
            'X-Requested-With': 'XMLHttpRequest',
            'X-Response-Format': 'JSONStream',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'm_ts': int(time.time()),
            'li': soup.find('input', {'name': 'li'})['value'],
            'try_number': '0',
            'unrecognized_tries': '0',
            'email': username,
            'pass': password,
            'prefill_contact_point': username,
            'prefill_source': 'browser_dropdown',
            'prefill_type': 'contact_point',
            'first_prefill_source': 'browser_dropdown',
            'first_prefill_type': 'contact_point',
            'had_cp_prefilled': 'true',
            'had_password_prefilled': 'false',
            'm_sess': '',
            'fb_dtsg': re.findall(re.compile(r'{"dtsg":{"token":"(.*?)"'), resp.text)[0],
            'lsd': soup.find('input', {'name': 'lsd'})['value'],
            # '__dyn':'',
            '__req': '6',
            '__ajax__': re.findall(re.compile(r'"encrypted":"(.*?)"'), resp.text)[0],
            '__user': '0'
        }
        session.post(url, data=data, headers=headers, verify=False)
        cookie = dict()
        [cookie.update({key: value}) for key, value in session.cookies.items()]
        if 'c_user' in cookie:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            key = 'cookie:facebook:{username}'.format(username=username)
            cookie.update({'create_at': arrow.now().format()})
            redis_client.set(key, cookie)
            redis_client.expire(key, 60 * 60 * 24 * 7)
    except:
        traceback.print_exc()


if __name__ == '__main__':
    get_cookie('username', 'password')
