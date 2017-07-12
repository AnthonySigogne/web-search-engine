#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API - a simple web search engine.
The goal is to index an infinite list of URLs (web pages), and then be able to quickly search relevant URLs against a query.

- Indexing :
The indexing operation of a new URL first crawls URL, then extracts the title and main text content from the page.
Then, a new document representing the URL's data is saved in ElasticSearch, and goes for indexing.

- Searching :
When searching for relevant URLs, the search engine will compare the query with the data in each document (web page),
and retrieve a list of URLs matching the query and sorted by relevance.

This API works for a finite list of languages, see here for the complete list : https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-lang-analyzer.html.
"""

__author__ = "Anthony Sigogne"
__copyright__ = "Copyright 2017, Byprog"
__email__ = "anthony@byprog.com"
__license__ = "MIT"
__version__ = "1.0"

import os
import url
import crawler
from flask import Flask, request, jsonify
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import Index, Search, Mapping
from elasticsearch_dsl.query import Q
from language import languages
from redis import Redis
from rq import Queue
from rq.decorators import job
from scrapy.crawler import CrawlerProcess
from urllib.parse import urlparse

# init flask app and import helper
app = Flask(__name__)
with app.app_context():
    from helper import *

# initiate the elasticsearch connection
hosts = [os.getenv("HOST")]
http_auth = (os.getenv("USERNAME"), os.getenv("PASSWORD"))
port = os.getenv("PORT")
client = connections.create_connection(hosts=hosts, http_auth=http_auth, port=port)

# initiate Redis connection
redis_conn = Redis(os.getenv("REDIS_HOST"), os.getenv("REDIS_PORT"))

# create ElasticSearch mapping of a web page for each language
for lang in languages :
    # index named "web-<language code>"
    index = Index('web-%s'%lang)
    if not index.exists() :
        index.create()

    # mapping of page
    m = Mapping('page')
    m.field('url', 'text', analyzer=languages[lang])
    m.field('title', 'text', analyzer=languages[lang])
    m.field('description', 'text', analyzer=languages[lang])
    m.field('body', 'text', analyzer=languages[lang])

    # save the mapping in index
    m.save('web-%s'%lang)

@app.route("/index", methods=['POST'])
def index():
    """
    URL : /index
    Index a new URL in search engine.
    Method : POST
    Form data :
        - url : the url to index [string, required]
    Return a success message.
    """
    # get POST data
    data = dict((key, request.form.get(key)) for key in request.form.keys())
    if "url" not in data :
        raise InvalidUsage('No url specified in POST data')

    # crawl url
    url_data = url.crawl(data["url"])
    if not url_data :
        raise InvalidUsage("URL is invalid or has no text inside")

    # get main language of page
    lang = url.detect_language(url_data.text)
    if lang not in languages :
        raise InvalidUsage('Language not supported')

    # extract title of url
    title = url.extract_title(url_data.text)

    # extract description of url
    description = url.extract_description(url_data.text)

    # extract main content of url
    body = url.extract_content(url_data.text, languages.get(lang))

    # if no description, try to artificially create one from main content
    if not description :
        description = url.create_description(body)

    # index url and data
    res = client.index(index="web-%s"%lang, doc_type='page', id=data["url"], body={
        "title":title,
        "description":description,
        "body":body,
        "url":url_data.url
    })

    return "Success"

@job('default', connection=redis_conn)
def explore_job(link) :
    """
    Explore a website and index all urls (redis-rq process).
    """
    print("explore website at : %s"%link)

    # get final url after possible redictions
    try :
        link = url.crawl(link).url
    except :
        return 0

    # start crawler
    process = CrawlerProcess({
        'USER_AGENT': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36",
        'DOWNLOAD_TIMEOUT':100,
        'DOWNLOAD_DELAY':0.25,
        'ROBOTSTXT_OBEY':True,
        'HTTPERROR_ALLOW_ALL':True,
        'HTTPCACHE_ENABLED':False,
        'REDIRECT_ENABLED':False,
        'SPIDER_MIDDLEWARES' : {
            'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware':True,
            'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware':True,
            'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware':True,
            'scrapy.extensions.closespider.CloseSpider':True
        },
        'CLOSESPIDER_PAGECOUNT':500 #only for debug
    })
    process.crawl(crawler.Crawler, allowed_domains=[urlparse(link).netloc], start_urls = [link,], es_client=client)
    process.start()

    return 1

@app.route("/explore", methods=['POST'])
def explore():
    """
    URL : /explore
    Explore a website and index all urls
    Method : POST
    Form data :
        - url : the url to explore [string, required]
    Return a success message (means redis-rq process launched).
    """
    # get POST data
    data = dict((key, request.form.get(key)) for key in request.form.keys())
    if "url" not in data :
        raise InvalidUsage('No url specified in POST data')

    # launch exploration job
    explore_job.delay(data["url"])

    return "Exploration started"

@app.route("/search", methods=['POST'])
def search():
    """
    URL : /search
    Query engine to find a list of relevant URLs.
    Method : POST
    Form data :
        - query : the search query [string, required]
        - hits : the number of hits returned by query [integer, optional, default:10]
        - start : the start of hits [integer, optional, default:0]
        - highlight : return highlight parts for each URL [integer, optional, default:0]
    Return a sublist of matching URLs sorted by relevance, and the total of matching URLs.
    """
    # get POST data
    data = dict((key, request.form.get(key)) for key in request.form.keys())
    if "query" not in data :
        raise InvalidUsage('No query specified in POST data')
    start = int(data.get("start", "0"))
    hits = int(data.get("hits", "10"))
    if start < 0 or hits < 0 :
        raise InvalidUsage('Start or hits cannot be negative numbers')
    highlight = int(data.get("highlight", "0"))

    # query search engine
    s = Search(index="web-*").using(client).highlight('title', 'description', 'body', pre_tags="<b>", post_tags="</b>", fragment_size=180)
    q = Q("multi_match", query=data["query"], fields=['title', 'description', 'body'])
    s = s.query(q)[start:start+hits]

    """for hit in s :
        try :
            #print(hit.url, hit.body)
            print(hit.url, hit.meta.score)
        except :
            pass"""

    def format_result(hit) :
        """
        Format a query hit.
        """
        title = description = None
        if highlight and "highlight" in hit.meta :
            if "description" in hit.meta.highlight :
                description = hit.meta.highlight.description[0]+"..."
            elif "body" in hit.meta.highlight :
                description = hit.meta.highlight.body[0]+"..."
            if "title" in hit.meta.highlight :
                title = hit.meta.highlight.title[0]

        return {
            "url":hit.url,
            "title":title if title else hit.title,
            "description":description if description else hit.description
        }

    # return list of matching results
    return jsonify(total=s.count(), results=[format_result(hit) for hit in s])
