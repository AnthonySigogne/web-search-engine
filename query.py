#!/usr/bin/env python
# -*- coding: utf-8 -*-

def expression_query(expression) :
    return {
      "query": {
        "multi_match" : {
          "query":    expression,
          "type":       "best_fields",
          "fields": [ "title^3", "description^2", "body" ]
        }
      },
      "rescore" : [{
          "query" : {
             "rescore_query" : {
                "multi_match" : {
                  "query": expression,
                  "type":       "cross_fields",
                  "fields": [ "title", "description", "body" ],
                  "minimum_should_match":"100%"
                }
             },
             "query_weight" : 0.5,
             "rescore_query_weight" : 1.5
          }
       },
       {
          "query" : {
             "score_mode": "multiply",
             "rescore_query" : {
                "function_score" : {
                   "script_score": {
                      "script": {
                        "inline": "_score*doc.weight.value"
                      }
                   }
                }
             }
          }
       } ],
      "size": 0,
      "aggs":{
        "per_domain":{
          "terms": {
            "field": "domain",
            "order": {
              "top_hit": "desc"
            }
          },
          "aggs": {
                "top_results": {
                    "top_hits": {
                        "highlight" : {
                            "pre_tags" : ["<b>"],
                            "post_tags" : ["</b>"],
                            "fields" : {
                                "title" : {"fragment_size" : 180},
                                "description" : {"fragment_size" : 180},
                                "body" : {"fragment_size" : 180}
                            }
                        }
                    }
                },
                "top_hit" : {
                  "max": {
                    "script": {
                      "inline": "_score"
                    }
                  }
                }
            }
        }
      }
    }

def domain_query(domain) :
    return {
        "query": {
            "term" : { "domain":domain}
        },
        "sort" : [
          {"weight" : {"order" : "desc"}}
        ]
    }

def domain_expression_query(domain, expression) :
    return {
        "query": {
            "bool":{
                "must":{
                    "multi_match" : {
                      "query":    expression,
                      "type":       "best_fields",
                      "fields": [ "title^3", "description^2", "body" ]
                    }
                },
                "filter":{
                    "term": {"domain": domain}
                }
            }
        },
        "highlight" : {
            "pre_tags" : ["<b>"],
            "post_tags" : ["</b>"],
            "fields" : {
                "title" : {"fragment_size" : 180},
                "description" : {"fragment_size" : 180},
                "body" : {"fragment_size" : 180}
            }
        },
        "rescore" : [{
          "query" : {
             "rescore_query" : {
                "multi_match" : {
                  "query": expression,
                  "type":       "cross_fields",
                  "fields": [ "title", "description", "body" ],
                  "minimum_should_match":"100%"
                }
             },
             "query_weight" : 0.5,
             "rescore_query_weight" : 1.5
          }
        },
        {
          "query" : {
             "score_mode": "multiply",
             "rescore_query" : {
                "function_score" : {
                   "script_score": {
                      "script": {
                        "inline": "_score*doc.weight.value"
                      }
                   }
                }
             }
          }
        } ]
    }
