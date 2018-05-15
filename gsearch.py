#!/usr/bin/python
# -*- coding: utf-8 -*-
# google search results crawler

import sys
import chardet
import os
import urlparse

reload(sys)
sys.setdefaultencoding('utf-8')

import threading
import urllib2, socket, time
import gzip, StringIO
import re, random, types
import socks
import socket
from bs4 import BeautifulSoup
from Configure import *

proxy_handler = urllib2.ProxyHandler({'http': 'http://%s:%s' % (PROXY_IP, str(PROXY_PORT)),
                                      'https': 'https://%s:%s' % (PROXY_IP, str(PROXY_PORT))})
opener = urllib2.build_opener(proxy_handler, urllib2.HTTPHandler)
urllib2.install_opener(opener)

def mkdir(path):
    # 去除首位空格
    path = path.strip()
    # 去除尾部 \ 符号
    path = path.rstrip("\\")

    # 判断路径是否存在
    # 存在     True
    # 不存在   False
    isExists = os.path.exists(path)

    # 判断结果
    if not isExists:
        # 如果不存在则创建目录
        # 创建目录操作函数
        os.makedirs(path)
        print path + ' 创建成功'
        return True
    else:
        # 如果目录存在则不创建，并提示目录已存在
        print path + ' 目录已存在'
        return False

# results from the search engine
# basically include url, title,content
class SearchResult:
    def __init__(self):
        self.url = ''
        self.title = ''
        self.content = ''

    def getURL(self):
        return self.url

    def setURL(self, url):
        self.url = url

    def getTitle(self):
        return self.title

    def setTitle(self, title):
        self.title = title

    def getContent(self):
        return self.content

    def setContent(self, content):
        self.content = content

    def printIt(self, prefix=''):
        print 'url\t->', self.url
        print 'title\t->', self.title
        # print 'content\t->', self.content


class GoogleAPI:
    def __init__(self):
        timeout = 20
        socket.setdefaulttimeout(timeout)
        self.results_per_page = 10
        self.base_url = 'https://www.google.com'
        self.user_agents = [
            "Mozilla/5.0 (Windows; U; Win98; en-US; rv:1.7.3) Gecko/20040910",
            "Mozilla/5.0 (Windows; U; Win95; en-US; rv:1.4) Gecko/20030624 Netscape/7.1",
            "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8b5) Gecko/20051006 Firefox/1.4.1",
            "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.0.0) Gecko/20021004"
        ]

    def randomSleep(self):
        sleeptime = random.randint(5, 10)
        time.sleep(sleeptime)

    # extract the domain of a url
    def extractDomain(self, url):
        domain = ''
        pattern = re.compile(r'http[s]?://([^/]+)/', re.U | re.M)
        url_match = pattern.search(url)
        if (url_match and url_match.lastindex > 0):
            domain = url_match.group(1)

        return domain

    # extract a url from a link
    def extractUrl(self, href):
        url = ''
        pattern = re.compile(r'(http[s]?://[^&]+)&', re.U | re.M)
        url_match = pattern.search(href)
        if (url_match and url_match.lastindex > 0):
            url = url_match.group(1)
        return url

    # extract serach results list from downloaded html file
    def extractSearchResults(self, html):
        results = list()
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div', id='search')
        if (type(div) != types.NoneType):
            lis = div.findAll('div', {'class': 'g'})
            if (len(lis) > 0):
                for li in lis:
                    result = SearchResult()
                    h3 = li.find('h3', {'class': 'r'})
                    if (type(h3) == types.NoneType):
                        continue

                    # extract domain and title from h3 object
                    link = h3.find('a')
                    if (type(link) == types.NoneType):
                        continue

                    url = link['href']
                    url = self.extractUrl(url)
                    if (cmp(url, '') == 0):
                        continue
                    title = link.renderContents()
                    result.setURL(url)
                    result.setTitle(title)

                    span = li.find('span', {'class': 'st'})
                    if (type(span) != types.NoneType):
                        content = span.renderContents()
                        result.setContent(content)
                    results.append(result)
        return results

    # search web
    # @param query -> query key words
    # @param lang -> language of search results
    # @param num -> number of search results to return
    def search(self, query, num, lang='en'):
        search_results = list()
        # proxy = urllib2.ProxyHandler({'https': '127.0.0.1:8087'})
        # opener = urllib2.build_opener(proxy)
        # urllib2.install_opener(opener)
        query = urllib2.quote(query.encode('utf-8'))
        if (num % self.results_per_page == 0):
            pages = num / self.results_per_page
        else:
            pages = num / self.results_per_page + 1

        for p in range(0, pages):
            start = p * self.results_per_page
            url = '%s/search?hl=%s&num=%d&start=%s&q=%s' % (self.base_url, lang, self.results_per_page, start, query)
            print url
            retry = 2
            while (retry > 0):
                try:
                    request = urllib2.Request(url)
                    length = len(self.user_agents)
                    index = random.randint(0, length - 1)
                    user_agent = self.user_agents[index]
                    request.add_header('user-agent', user_agent)
                    request.add_header('connection', 'keep-alive')
                    request.add_header('accept-encoding', 'gzip')
                    request.add_header('referer', self.base_url)
                    response = urllib2.urlopen(request)
                    html = response.read()
                    if (response.headers.get('content-encoding', None) == 'gzip'):
                        html = gzip.GzipFile(fileobj=StringIO.StringIO(html)).read()
                    results = self.extractSearchResults(html)
                    # print results
                    search_results.extend(results)
                    break
                except urllib2.URLError, e:
                    print 'url error:', e
                    self.randomSleep()
                    retry = retry - 1
                    continue

                except Exception, e:
                    print '1111error:', e
                    retry = retry - 1
                    self.randomSleep()
                    continue
        return search_results

class ThreadCrawl(threading.Thread):
    def __init__(self, expect_num, keyword, store):
        threading.Thread.__init__(self)
        self.api = GoogleAPI()
        self.expect_num = expect_num
        self.keyword = keyword
        self.base_url = 'https://www.google.com'
        self.results_per_page = 10
        self.user_agents = [
            "Mozilla/5.0 (Windows; U; Win98; en-US; rv:1.7.3) Gecko/20040910",
            "Mozilla/5.0 (Windows; U; Win95; en-US; rv:1.4) Gecko/20030624 Netscape/7.1",
            "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8b5) Gecko/20051006 Firefox/1.4.1",
            "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.0.0) Gecko/20021004"
        ]

        self.store = store

    def crawl_url_content(self, url):
        # proxy = urllib2.ProxyHandler({'https': '127.0.0.1:8087'})
        # opener = urllib2.build_opener(proxy)
        # urllib2.install_opener(opener)

        retry = 2
        while (retry > 0):
            try:
                request = urllib2.Request(url)
                length = len(self.user_agents)
                index = random.randint(0, length - 1)
                user_agent = self.user_agents[index]
                request.add_header('user-agent', user_agent)
                request.add_header('connection', 'keep-alive')
                request.add_header('accept-encoding', 'gzip')
                request.add_header('referer', self.base_url)
                response = urllib2.urlopen(request)
                html = response.read()
                if (response.headers.get('content-encoding', None) == 'gzip'):
                    html = gzip.GzipFile(fileobj=StringIO.StringIO(html)).read()
                char_type = chardet.detect(html)
                # print char_type
                if char_type["encoding"] != 'utf-8':
                    html = html.decode(char_type["encoding"]).encode("utf-8")
                return 1, html
            except urllib2.URLError, e:
                print 'url error:', e
                retry = retry - 1
                if (retry == 0):
                    return 0, e;
                continue

            except Exception, e:
                print 'error:', e
                retry = retry - 1
                if (retry == 0):
                    return 0, e;
                continue

    def run(self):
        one_record = self.keyword
        if (one_record != None):
            keyword = one_record
            print keyword
            results = self.api.search(keyword, num=self.expect_num)
            count = 0
            record = {}
            record["name"] = keyword
            # 定义要创建的目录
            mkpath = self.store + ":\\google_search_result\\" + keyword
            # 调用函数
            mkdir(mkpath)
            for r in results:
                r.printIt()
                status, content = self.crawl_url_content(r.getURL())
                d = {}
                d["url"] = r.url.encode("utf-8")
                if (status == 1):
                    count += 1
                    catalog = self.store + ":\\google_search_result\\" + keyword + "\\" + "web_" + str(count) + "\\"
                    mkdir(catalog)
                    url = urlparse.urlsplit(r.getURL()).netloc
                    file_object = open(catalog + url + ".html", 'w+')
                    file_object.write(content)
                    file_object.close()
