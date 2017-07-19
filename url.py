#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Toolbox for URLs.
"""

__author__ = "Anthony Sigogne"
__copyright__ = "Copyright 2017, Byprog"
__email__ = "anthony@byprog.com"
__license__ = "MIT"
__version__ = "1.0"

import re
import langdetect
import html2text
import requests
import justext
import tldextract
from html import unescape

def domain(url) :
    """
    Get the domain of the url.
    """
    return tldextract.extract(url).registered_domain

def crawl(url) :
    """
    Crawl an URL.
    Return URL data.
    """
    try :
        r = requests.get(url)
    except :
        return None
    return r

def detect_language(html) :
    """
    Detect the language of the text content of a page.
    """
    # handle string, need bytes
    try :
        html = html.decode("utf8")
    except :
        try :
            html = html.decode("latin1")
        except :
            pass
    h = html2text.HTML2Text()
    return langdetect.detect(h.handle(html))

def extract_content(html, lang) :
    """
    Extract the main text content of a page by removing boilerplate parts.
    """
    body = []
    boilerplate = []
    paragraphs = justext.justext(html, justext.get_stoplist(lang[:1].upper()+lang[1:]))
    for p in paragraphs :
        if p.text.count(" ") >= 5 :
            body.append(p.text)
        else :
            boilerplate.append(p.text)
    return ". ".join(body), ". ".join(boilerplate)

def extract_title(html) :
    """
    Extract the title of a page.
    """
    try :
        title = unescape(re.search("<title>([^<]+)</title>", html).group(1))
    except :
        title = None # no title on page
    return title

def extract_description(html) :
    """
    Extract the description of a page.
    """
    try :
        description = unescape(re.search('<meta name="[^">]*description"[^">]*content="([^">]+)',html).group(1))
    except :
        description = None # no description on page
    return description

def create_description(body) :
    """
    Artificially create a description from main content of page (only, in case of no meta description).
    """
    # extract all long sentences (possible candidates)
    candidates = sorted([sentence for sentence in body.split('.')],key=lambda s : s.count(" "), reverse=True)

    # return the best candidate or nothing
    if not candidates :
        return None
    return candidates[0]
