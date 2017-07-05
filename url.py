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
from html import unescape

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
    h = html2text.HTML2Text()
    return langdetect.detect(h.handle(html))

def extract_content(html, lang) :
    """
    Extract the main text content of a page by removing boilerplate parts.
    """
    paragraphs = justext.justext(html, justext.get_stoplist(lang[:1].upper()+lang[1:]))
    body = ". ".join([paragraph.text for paragraph in paragraphs if not paragraph.is_boilerplate])
    if not body :
        # error, return all paragraphs
        body = ". ".join([paragraph.text for paragraph in paragraphs])
    return body

def extract_title(html) :
    """
    Extract the title of a page.
    """
    try :
        title = unescape(re.search("<title>([^<]+)</title>", html).group(1))
    except :
        title = "" # no title on page
    return title

def extract_description(html) :
    """
    Extract the description of a page.
    """
    try :
        description = unescape(re.search('<meta name="[^">]*description"[^">]*content="([^">]+)',html).group(1))
    except :
        description = "" # no description on page
    return description
