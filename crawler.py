#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import url
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from language import languages

class Crawler(scrapy.spiders.CrawlSpider):
    """
    Explore a website and index all urls.
    """
    name = 'crawler'
    handle_httpstatus_list = [301, 302, 303]
    rules = (
        # Extract all inner domain links with state "follow"
        Rule(LinkExtractor(), callback='parse_items', follow=True, process_links='links_processor'),
    )
    es_client=None

    def links_processor(self,links):
        """
        A hook into the links processing from an existing page, done in order to not follow "nofollow" links
        """
        ret_links = list()
        if links:
            for link in links:
                if not link.nofollow:
                    ret_links.append(link)
        return ret_links

    def parse_items(self, response):
        """
        Parse and analyze one url of website.
        """
        # skip rss or atom urls
        if not response.css("html").extract_first() :
            return

        # extract title
        title = response.css('title::text').extract_first()
        title = title.strip() if title else ""

        # extract description
        description = response.css("meta[name=description]::attr(content)").extract_first()
        description = description.strip() if description else ""

        # get main language of page, and main content of page
        lang = url.detect_language(response.body.decode('utf8'))
        if lang not in languages :
            raise InvalidUsage('Language not supported')
        body = url.extract_content(response.body, languages.get(lang))

        # if no description, try to artificially create one from main content
        if not description :
            description = url.create_description(body)

        # url is not "interesting", not enough content, pass
        if not title and not description :
            return None

        # index url and data
        res = self.es_client.index(index="web-%s"%lang, doc_type='page', id=response.url, body={
            "title":title,
            "description":description,
            "body":body,
            "url":response.url
        })

        # check for redirect url
        if response.status in self.handle_httpstatus_list and 'Location' in response.headers:
            newurl = response.headers['Location']
            meta = {'dont_redirect': True, "handle_httpstatus_list" : self.handle_httpstatus_list}
            meta.update(response.request.meta)
            return Request(url = newurl.decode("utf8"), meta = meta, callback=self.parse)
