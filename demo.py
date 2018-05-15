#!/usr/bin/python
# -*- coding: utf-8 -*-

from gsearch import ThreadCrawl

if __name__ == "__main__":
    crawler = ThreadCrawl(50, "Tom Cruise", "D")
    crawler.start()