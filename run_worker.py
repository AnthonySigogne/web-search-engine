#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function, unicode_literals)

import os
from rq import Connection, Queue, Worker
from redis import Redis

if __name__ == '__main__':
    # Tell rq what Redis connection to use
    with Connection(connection=Redis(os.getenv("REDIS_HOST", "redis"), os.getenv("REDIS_PORT", 6379))):
        q = Queue()
        Worker(q).work()
