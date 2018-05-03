# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class FacebookItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class UserItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    nick_name = scrapy.Field()
    home = scrapy.Field()
    account_name = scrapy.Field()
    portrait = scrapy.Field()
    introduce = scrapy.Field()


class PublicPageItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    nick_name = scrapy.Field()
    home = scrapy.Field()
    account_name = scrapy.Field()
    portrait = scrapy.Field()
    introduce = scrapy.Field()
    type = scrapy.Field()


class FriendsItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    user_id = scrapy.Field()
    type_ = scrapy.Field()
    friends_lst = scrapy.Field()
