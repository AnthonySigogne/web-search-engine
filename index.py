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

import re
import os
import url
import crawler
import requests
import json
import query
from flask import Flask, request, jsonify
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import Index, Search, Mapping
from language import languages
from redis import Redis
from rq import Queue
from rq.decorators import job
from scrapy.crawler import CrawlerProcess
from urllib.parse import urlparse
from datetime import datetime

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
redis_conn = Redis(os.getenv("REDIS_HOST", "redis"), os.getenv("REDIS_PORT", 6379))

# create indices and mappings
for lang in ["fr"] : #languages :
    # index named "web-<language code>"
    index = Index('web-%s'%lang)
    if not index.exists() :
        index.create()

    # mapping of page
    m = Mapping('page')
    m.field('url', 'keyword')
    m.field('domain', 'keyword')
    m.field('title', 'text', analyzer=languages[lang])
    m.field('description', 'text', analyzer=languages[lang])
    m.field('body', 'text', analyzer=languages[lang])
    m.field('weight', 'long')
    #m.field('keywords', 'completion') # -- TEST -- #
    m.save('web-%s'%lang)

# index for misc mappings
index = Index('web')
if not index.exists() :
    index.create()

# mapping of domain
m = Mapping('domain')
m.field('homepage', 'keyword')
m.field('domain', 'keyword')
m.field('last_crawl', 'date')
#m.field('keywords', 'text', analyzer=languages[lang])
m.save('web')

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

    # launch exploration job
    index_job.delay(data["url"])

    return "Indexing started"

@job('default', connection=redis_conn)
def index_job(link) :
    """
    Index a single page.
    """
    print("index page : %s"%link)

    # get final url after possible redictions
    try :
        link = url.crawl(link).url
    except :
        return 0

    process = CrawlerProcess({
        'USER_AGENT': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36",
        'DOWNLOAD_TIMEOUT':100,
        'REDIRECT_ENABLED':False,
        'SPIDER_MIDDLEWARES' : {
            'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware':True
        }
    })
    process.crawl(crawler.SingleSpider, start_urls=[link,], es_client=client)
    process.start() # block until finished

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

    # create or update domain data
    domain = url.domain(link)
    res = client.index(index="web", doc_type='domain', id=domain, body={
        "homepage":link,
        "domain":domain,
        "last_crawl":datetime.now()
    })

    # start crawler
    process = CrawlerProcess({
        'USER_AGENT': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36",
        'DOWNLOAD_TIMEOUT':100,
        'DOWNLOAD_DELAY':0.25,
        'ROBOTSTXT_OBEY':True,
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
    Return a sublist of matching URLs sorted by relevance, and the total of matching URLs.
    """
    def format_result(hit, highlight) :
        # highlight title and description
        title = hit["title"]
        description = hit["description"]
        if highlight :
            if "description" in highlight :
                description = highlight["description"][0]+"..."
            elif "body" in highlight :
                description = highlight["body"][0]+"..."
            if "title" in highlight :
                title = highlight["title"][0]

        # create false title and description for better user experience
        if not title :
            title = hit["domain"]
        if not description :
            description = url.create_description(hit["body"])+"..."

        return {
            "title":title,
            "description":description,
            "url":hit["url"]
        }

    # get POST data
    data = dict((key, request.form.get(key)) for key in request.form.keys())
    if "query" not in data :
        raise InvalidUsage('No query specified in POST data')
    start = int(data.get("start", "0"))
    hits = int(data.get("hits", "10"))
    if start < 0 or hits < 0 :
        raise InvalidUsage('Start or hits cannot be negative numbers')

    # analyze user query
    groups = re.search("(site:(?P<domain>[^ ]+))?( ?(?P<query>.*))?",data["query"]).groupdict()
    if groups.get("query", False) and groups.get("domain", False) :
        # expression in domain query
        response = client.search(index="web-*", doc_type="page", body=query.domain_expression_query(groups["domain"], groups["query"]), from_=start, size=hits)
        results = [format_result(hit["_source"], hit.get("highlight", None)) for hit in response["hits"]["hits"]]
        total = response["hits"]["total"]

    elif groups.get("domain", False) :
        # domain query
        response = client.search(index="web-*", doc_type="page", body=query.domain_query(groups["domain"]), from_=start, size=hits)
        results = [format_result(hit["_source"], None) for hit in response["hits"]["hits"]]
        total = response["hits"]["total"]

    elif groups.get("query", False) :
        # expression query
        response = client.search(index="web-*", doc_type="page", body=query.expression_query(groups["query"]))
        results = []
        for domain_bucket in response['aggregations']['per_domain']['buckets']:
            for hit in domain_bucket["top_results"]["hits"]["hits"] :
                results.append((format_result(hit["_source"], hit.get("highlight", None)),hit["_score"]))
        results = [result[0] for result in sorted(results, key=lambda result: result[1], reverse=True)]
        total = len(results)
        results = results[start:start+hits]

    return jsonify(total=total, results=results)
