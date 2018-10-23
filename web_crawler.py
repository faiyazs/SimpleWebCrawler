import mimetypes
import re
import urllib
import queue as pqueue
import urllib.request
import urllib.robotparser as robotparser
from urllib.parse import urljoin
from url_normalize import url_normalize
from collections import deque
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import time
from multiprocessing import Process
import requests
import datetime


# ignoring media type files
ignoredMimeTypeList = ["image/mng", "image/bmp", "image/gif", "image/jpg", "image/jpeg", "image/png", "image/pst",
                       "image/psp", "image/fif", "image/tiff", "image/ai", "image/drw", "image/x-dwg", "audio/mp3",
                       "audio/wma", "audio/mpeg", "audio/wav", "audio/midi", "audio/mpeg3", "audio/mp4",
                       "audio/x-realaudio", "video/3gp", "video/avi", "video/mov", "video/mp4", "video/mpg",
                       "video/mpeg", "video/wmv", "text/css", "application/x-pointplus", "application/pdf",
                       "application/octet-stream", "application/x-binary", "application/zip"]


# Queue for BFS and PriorityQueue for Focused Crawler
queue = deque()
mainqueue = deque()
nqueue = pqueue.PriorityQueue()
mainpqueue = pqueue.PriorityQueue()

redun_queue = deque()
redun_nqueue = deque()
# query to be searched
query = "brooklyn dodgers"


# Checking if the link must be crawled of not ( Checking robots.txt file )
def parser(url):
    try:
        parsed_uri = urlparse(url)
        # Get the Domain name of the URL
        result = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        rp = robotparser.RobotFileParser()
        result += "robots.txt"
        rp.set_url(result)
        try:
            # Check if URL is Readable or not
            rp.read()
        except:
            pass
        # Checking if User Agent is allowed to parse or not
        if rp.can_fetch("*", url):
            return True
        else:
            return False
    except IOError:
        pass


# Fetching Results from Google using Pythons googlesearch library
def result(query):
    results = []

    try:
        from googlesearch import search
    except ImportError:
        print("No module named 'googlesearch' found")
    for j in search(query, tld="com", num=10, stop=1, pause=2):
        results.append(j)
    return results


# Cheking the type of website ( i.e jpeg or video or media website)
def mime(url):
    types = mimetypes.guess_type(url)
    # If unable to get the correct mimetype, extract manually
    if types is None:
        response = urllib.request.urlopen(url).info()
        strResponse = str(response)
        ind1 = strResponse.find('Content-Type:')
        ind2 = strResponse.find(' ', ind1)
        ind3 = strResponse.find(';', ind1)
        strResponse = strResponse[ind2:ind3].strip()
        if strResponse not in ignoredMimeTypeList:
            return True
    if types not in ignoredMimeTypeList:
        return True


# Normalizing URLS (i.e. if Two URL's are different in upercase or lowercase
def normalizeUrls(urls):
    normalized_urls = []
    try:
        for url in urls:
            normalized_urls.append(url_normalize(url))
        return normalized_urls
    except:
        pass


# Parsing the HTML file i.e reading the contents of the html file
def readHTML(url):
    try:
        page = urllib.request.urlopen(url)
        htmlText = page.read()
        if len(htmlText) > 0:
            return htmlText
    except IOError as errorcode:
        pass


# Finding the Relavence score of the website after crawling it
# (Counting the no. of times query word appears in HTML page / Len of HTML page ) + 0.5 * parentScore (initially 0)
def findScore(page, query, parentScore):
    try:
        count = 0
        totalCount = len(page.split())
        for word in query.split():  # print("page:", page.decode('utf-8'))
            a = page.decode('utf-8')
            # for pageword in a.split():
            if word in a.lower().split():
                count += 1
        score = (float(count) / totalCount) + (0.5 * parentScore)
        if score is not None:
            score = score
        else:
            score = 0
        return score
    except:
        pass


# Function to find Promise of a website in Focused Crawling
# Similar formula to relevance (checking the words of query in the URL)
def findpromScore(page, query, parentScore):
    try:
        count = 0
        totalCount = len(page.split())
        for word in query.lower().split():
            if word in page:
                count += 1
        score = ((float(count) / totalCount)*0.1) + (0.5 * parentScore)
        if score is not None:
            score = score
        else:
            score = 0
        return score
    except:
        pass


# Function to find links present in a website for crawling
# This function finds all the HTTPS and HTTP links in a website
def linkOfPage(url):
    a = []
    links = []
    try:
        request = urllib.request.Request(url, None, {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36'})
        html_page = urllib.request.urlopen(request)
        soup = BeautifulSoup(html_page, 'html.parser')
        for link in soup.findAll('a', attrs={'href': re.compile("^http://")}):
            if link is not None or link == {} or link:
                a.append(link.get('href'))
        for link in soup.findAll('a', attrs={'href': re.compile("^https://")}):
            if link is not None or link == [] or link:
                a.append(link.get('href'))
        for i in range(len(a)):
            a[i] = urljoin(url, a[i])
            if not a[i]:
                pass
            links.append(a[i])
        return links
    except:
        pass


# Getting the title of URL PAge
def anchor(url):
    s = ''
    soup = BeautifulSoup(urllib.request.urlopen(url), "html.parser")
    try:
        for link in soup.findAll('title'):
            s += link.string + ' '
    except:
        pass
    return s


''' Function to Perform BFS crawling 
    This function initially gets the first links from googlesearch library and 
    checks if those links are crawlable or not and finds the Relevance Score and appends to Queue
    after Appending to Queue , It calls bfs_parse to perform BFS functionality '''


def bfs(total_pages):
    try:
        t = str(datetime.datetime.now())
        to_find = set()
        links = result(query)
        print("Here 111")
        links = normalizeUrls(links)
        # Initialize Depth value as 3
        depth1 = 3
        page = None
        item = None
        r = None
        for index in range(len(links)):  # for the top 10 links parse the HTMl content and return the score and links
            # get links present inside page and check if they are crawlable or not
            isCrawlable = parser(links[index])
            isCorrect = mime(links[index])
            r = requests.get(links[index], allow_redirects=False)
            if isCrawlable and isCorrect:
                page = readHTML(links[index])
            if page is not None and r is not None:
                score = findScore(page, query, 0)
                # storing score , link and depth in a list
                item = [score, links[index], 1, datetime.datetime.now(), r]
            if item is not None:
                # appending the item to Queues
                mainqueue.append(item)
                queue.append(item)
                to_find.add(links[index])
        # Calling bfs_parse to perform BFS Functionality
        bfs_parse(depth1, total_pages, queue, to_find)
        count = 0
        alt = []
        log_file = open('./logs/bfscrawler_2.dat', 'w+')
        # inserting all Queue items in a list and printing in log file
        while mainqueue:
            count += 1
            item = mainqueue.popleft()
            log_file.write('----------------------------------------------------------------------------------------\n')
            log_file.write(f'Relevance Score :               {item[0]}\n')
            log_file.write(f'Link Parsed     :               {item[1]}\n')
            log_file.write(f'Depth           :               {item[2]}\n')
            log_file.write(f'Time            :               {item[3]}\n')
            log_file.write(f'Status          :               {item[4]}\n')
            log_file.write('\n\n')
            alt.append(item)
        # finding the maximum and minimum relevance score in the list
        maxx = max([lin[0] for lin in alt if lin[0] is not None])
        minn = min([lin[0] for lin in alt if lin[0] is not None])
        mid = float((minn + maxx) / 2)
        print("BFS", mid, minn, maxx)
        i1, i, i2 = 0, 0, 0
        responseCount = 0
        # Using a Threshold to find out Harvest Score , If the Relevance is above Threshold then link is relevant
        for i in range(len(alt)):
            if (alt[i][0]) is not None and (alt[i][0]) >= 0.00004:
                i1 += 1
            if "200" in str(alt[i][4]):
                i2 += 1
        print(len(alt))
        # Harvest Score
        score = i1/total_pages
        print("BFS SCORE = ", score)
        crawl_end_time = str(datetime.datetime.now())
        log_file.write('########################    Statistics    ########################\n\n')
        log_file.write(f'Crawl Start Time                       :               {t}\n')
        log_file.write(f'Crawl End Time                         :               {crawl_end_time}\n')
        log_file.write(f'Number of seed pages from Google       :               {len(links)}\n')
        log_file.write(f'Number pages crawled besides Google    :               {len(alt) - len(links)}\n')
        log_file.write(f'Number of non-200 responses            :               {len(alt)- i2}\n')
        log_file.write(f'Number of pages visited again          :               {len(redun_queue)}\n')
        log_file.write(f'Harvest Score                          :               {score}\n')
        log_file.close()
    except Exception as e:
        print(" error, ", e)


# Performing BFS crawling operation
def bfs_parse(depth1, total_pages, queue, to_find):
    total = total_pages - len(queue)
    page = None
    score = None
    item = None
    t = time.time()
    r = None
    redun = 0
    # unless queue is empty , perform operations
    while queue:
        try:
            # get the first link from the queue
            link = queue.popleft()
            # finding the links present inside the link
            new_links = linkOfPage(link[1])
            new_links = normalizeUrls(new_links)
            for i in range(len(new_links)):
                r = requests.get(new_links[i], allow_redirects=False)
                # checking the domain name to change the depth accordingly
                a = urlparse((new_links[i]))
                b = urlparse(link[1])
                if a.netloc != b.netloc:
                    depth2 = 1
                else:
                    depth2 = link[2] + 1
                # check if new link is crawlable or not
                isCrawlable = parser(new_links[i])
                isCorrect = mime(new_links[i])
                if isCrawlable and isCorrect:
                    page = readHTML(new_links[i])
                if page is not None:
                    # calculating the score of the child link
                    score = findScore(page, query, link[0])
                if new_links[i] in to_find:
                    print("Here 12")
                    redun_queue.append(0)
                # saving the score, link and depth in a list  and check if the link was already visited or not
                if new_links[i] not in to_find and score is not None and depth2 is not None:
                    item = [score, new_links[i], depth2, datetime.datetime.now(), r]
                else:
                    continue
                # inserting the given item in queue
                if item[2] <= depth1 and item is not None:
                    mainqueue.append(item)
                    queue.append(item)
                    to_find.add(new_links[i])
                    total -= 1
                    print("Total", total)
                else:
                    continue
                # check if the total number of links have been visited or not
                if total <= 0:
                    print("Here 15")
                    break
        except Exception as e:
            print(" error 2", e)
        if total <= 0:
            print("Here 16")
            break


''' Focused crawling is performed where the the links for goglesearch are checked if crawlable or not,
    inserted into PriorityQueue according to their promise(findpromScore) , initially setting the promise to -1
    and then ncrawl_parse function is called to perform BFS crawling but item is appended in the PriorityQueue
     according to their promise '''


def ncrawl(total_pages):
    t = datetime.datetime.now()
    links = result(query)
    links = normalizeUrls(links)
    # setting the initial depth to 3
    depth1 = 3
    # initial promise is 0
    promise = -1
    page = None
    item = None
    score = None
    to_find = set()
    r = None
    for index in range(len(links)):  # for the top 10 links parse the HTMl content and return the score and links
        # get links present inside page and check if the links are crawlable or not
        isCrawlable = parser(links[index])
        isCorrect = mime(links[index])
        r = requests.get(links[index], allow_redirects=False)
        if isCrawlable and isCorrect:
            page = readHTML(links[index])
        if page is not None:
            score = findScore(page, query, 0)
        if score is not None and r is not None:
            item = (promise, [score, links[index], 1, datetime.datetime.now(), r])
        if item is not None:
            mainpqueue.put(item)
            nqueue.put(item)
            to_find.add(links[index])
    # perform BFS crawling according the promise as priority
    ncrawl_parse(depth1, total_pages, nqueue, to_find)
    count = 0
    all1 = []
    log_file = open('./logs/focusedcrawler_2.dat', 'w+')
    # inserting all the PriorityQueue values to a list
    while not mainpqueue.empty():
        count += 1
        use = mainpqueue.get()
        log_file.write('----------------------------------------------------------------------------------------\n')
        log_file.write(f'Promise Score   :               {use[0]}\n')
        log_file.write(f'Relevance Score :               {use[1][0]}\n')
        log_file.write(f'Link Parsed     :               {use[1][1]}\n')
        log_file.write(f'Depth           :               {use[1][2]}\n')
        log_file.write(f'Time            :               {use[1][3]}\n')
        log_file.write(f'Status          :               {use[1][4]}\n')
        log_file.write('\n\n')
        # print(use)
        all1.append(use[1])
    c = 8
    maxx = max([lin[0] for lin in all1])
    minn = min([lin[0] for lin in all1])
    mid = float((minn + maxx) / c)
    i1, i, i2 = 0, 0, 0
    # using threshold value to calculate the harvest score of focused crawler
    for i in range(len(all1)):
        if (all1[i][0]) >= 0.000025:
            i1 += 1
        if "200" in str(all1[i][4]):
            i2 += 1
    score = i1 / total_pages
    print("FOCUSED CRAWLER SCORE = ", score)
    crawl_end_time = str(datetime.datetime.now())
    log_file.write('########################    Statistics    ########################\n\n')
    log_file.write(f'Crawl Start Time                       :               {t}\n')
    log_file.write(f'Crawl End Time                         :               {crawl_end_time}\n')
    log_file.write(f'Number of seed pages from Google       :               {len(links)}\n')
    log_file.write(f'Number pages crawled besides Google    :               {len(all1) - len(links)}\n')
    log_file.write(f'Number of non-200 responses            :               {len(all1)- i2}\n')
    log_file.write(f'Number of pages visited again          :               {len(redun_nqueue)}\n')
    log_file.write(f'Harvest Score                          :               {score}\n')
    log_file.close()


# This function performs BFS crawling according giving priority to the best promise websites
def ncrawl_parse(depth1, total_pages, nqueue, to_find):
    total = total_pages - nqueue.qsize()
    page = None
    score = None
    item = None
    prom = None
    promise_score = None
    r = None
    while not nqueue.empty():
        try:
            print("Here 21")
            # get the first link from the queue
            link = nqueue.get_nowait()
            new_links = linkOfPage(link[1][1])
            new_links = normalizeUrls(new_links)
            print("Here 22")
            for i in range(len(new_links)):
                r = requests.get(new_links[i], allow_redirects=False)
                # checking the netloc to change the depth of link accordingly
                a = urlparse((new_links[i]))
                b = urlparse(link[1][1])
                if a.netloc != b.netloc:
                    depth2 = 1
                else:
                    depth2 = link[1][2] + 1
                # check if link is crawlable or not
                isCrawlable = parser(new_links[i])
                isCorrect = mime(new_links[i])
                if isCrawlable and isCorrect:
                    page = readHTML(new_links[i])
                if page is not None:
                    # find promise and relevance of the link
                    promise_score = findpromScore(new_links[i], query, link[1][0])
                    score = findScore(page, query, link[1][0])
                # check if link is already crawled or not before
                if new_links[i] in to_find:
                    print("Here 32")
                    redun_nqueue.append(0)
                if (new_links[i] not in to_find) and (score is not None) and (promise_score is not None):
                    item = ((-promise_score), [score, new_links[i], depth2, datetime.datetime.now(), r])
                else:
                    continue
                # inserting the link to queue with promise and relevance score
                if item[1][2] <= depth1 and item is not None:
                    mainpqueue.put(item)
                    nqueue.put(item)
                    to_find.add(new_links[i])
                    total -= 1
                    print("total", total)
                # check it the total number of pages have been crawled or not and break
                if total <= 0:
                    break
        except:
            pass
        if total <= 0:
            break


if __name__ == '__main__':
    # timer function to calculate time
    t0 = datetime.datetime.now()
    # total number of pages to be crawled
    total_pages = 1000
    print("Query: ", query)
    print("Total Pages :", total_pages)
    # using multiprocessing to run both the BFS and focused crawler simultaneously
    p1 = Process(target=bfs(total_pages))
    p1.start()
    p2 = Process(target=ncrawl(total_pages))
    p2.start()
    p1.join()
    p2.join()
    t1 = datetime.datetime.now()
    print("Total Time = ", (t1 - t0))
