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

This API works for English, French and German URLs only.
"""

__author__ = "Anthony Sigogne"
__copyright__ = "Copyright 2017, Byprog"
__email__ = "anthony@byprog.com"
__license__ = "MIT"
__version__ = "1.0"

import os
import re
import justext
import requests
import html
from flask import Flask, request, jsonify
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl import Index, Search, Mapping
from elasticsearch_dsl.query import Q

# init flask app and import helper
app = Flask(__name__)
with app.app_context():
    from helper import *

# initiate the elasticsearch connection
hosts = [os.getenv("HOST")]
http_auth = (os.getenv("USERNAME"), os.getenv("PASSWORD"))
port = os.getenv("PORT")
client = connections.create_connection(hosts=hosts, http_auth=http_auth, port=port)

# declare a dictionary of languages (code -> long form)
languages = {
    "fr": "french",
    "en": "english",
    "de": "german"
}

# create mapping of a web page for each language
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
        - url : the url to index
        - language : language of url ("fr", "en" or "de")
    Return a success message.
    """
    # get POST data
    data = dict((key, request.form.get(key)) for key in request.form.keys())
    if "url" not in data :
        raise InvalidUsage('No url specified in POST data')
    if "language" not in data :
        raise InvalidUsage('No language specified in POST data')
    if data["language"] not in languages :
        raise InvalidUsage('Language not supported')

    # crawl url
    try :
        r = requests.get(data["url"])
    except :
        raise InvalidUsage("URL is invalid or has no text inside")

    # extract title of url
    try :
        title = html.unescape(re.search("<title>([^<]+)</title>", r.text).group(1))
    except :
        title = "" # no title on page

    # extract description of url
    try :
        description = html.unescape(re.search('<meta name="[^">]*description"[^">]*content="([^">]+)',r.text).group(1))
    except :
        description = "" # no description on page

    # extract main content of url
    lang = languages.get(data["language"])
    paragraphs = justext.justext(r.text, justext.get_stoplist(lang[:1].upper()+lang[1:]))
    body = ". ".join([paragraph.text for paragraph in paragraphs if not paragraph.is_boilerplate])

    # index url and data
    res = client.index(index="web-%s"%data["language"], doc_type='page', id=data["url"], body={
        "title":title,
        "description":description,
        "body":body,
        "url":data["url"]
    })

    return "Success"

@app.route("/search", methods=['POST'])
def search():
    """
    URL : /search
    Query engine to find a list of relevant URLs.
    Method : POST
    Form data :
        - query : the search query
        - hits : the number of hits returned by query
        - start : the start of hits
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

    # query search engine
    s = Search(index="web-*").using(client)
    q = Q("multi_match", query=data["query"], fields=['title', 'description', 'body'])
    s = s.query(q)[start:start+hits]

    # return list of matching results
    return jsonify(total=s.count(), results=[{"url":hit.url, "title":hit.title, "description":hit.description} for hit in s])
