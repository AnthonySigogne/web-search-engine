#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Flask Helper and custom invalid usage exception.
"""

__author__ = "Anthony Sigogne"
__copyright__ = "Copyright 2017, Byprog"
__email__ = "anthony@byprog.com"
__license__ = "MIT"
__version__ = "1.0"

from flask import current_app, jsonify

@current_app.route("/")
def helper():
    """
    URL : /
    Helper that list all services of API.
    """
    # print module docstring
    output = [__doc__.replace("\n","<br/>"),]

    # then, get and print docstring of each rule
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == "static" : # skip static endpoint
            continue
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)
        methods = ','.join(rule.methods)
        output.append(current_app.view_functions[rule.endpoint].__doc__.replace("\n","<br/>"))

    return "<br/>".join(output)

class InvalidUsage(Exception):
    """
    Custom invalid usage exception.
    """
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@current_app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    """
    JSON version of invalid usage exception
    """
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
