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
    "de": "german",
    "ro": "romanian",
    "ru": "russian",
    "ar": "arabic",
    "hi": "hindi",
    "es": "spanish",
    "fi": "finnish",
    "nl": "dutch",
    "cs": "czech",
    "ca": "catalan",
    "bg": "bulgarian",
    "pt": "portuguese",
    "da": "danish",
    "no": "norwegian",
    "sv": "swedish",
    "el": "greek",
    "th": "thai",
    "tr": "turkish",
    "it": "italian",
    "ga": "irish",
    "hu": "hungarian",
    "lt": "lithuanian",
    "id": "indonesian",
    "fa": "persian",
    "lv": "latvian"
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

    # index url and data
    res = client.index(index="web-%s"%lang, doc_type='page', id=data["url"], body={
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
    s = Search(index="web-*").using(client).highlight('title', 'description', pre_tags="<b>", post_tags="</b>")
    q = Q("multi_match", query=data["query"], fields=['title', 'description', 'body'])
    s = s.query(q)[start:start+hits]

    # return list of matching results
    return jsonify(total=s.count(), results=[{
        "url":hit.url,
        "title":hit.meta.highlight.title[0] if highlight and "highlight" in hit.meta and "title" in hit.meta.highlight else hit.title,
        "description":hit.meta.highlight.description[0] if highlight and "highlight" in hit.meta and "description" in hit.meta.highlight else hit.description
        } for hit in s])
