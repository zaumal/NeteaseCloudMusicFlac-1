# -*- coding: utf-8 -*-
import re

import logging
import requests
import json
import urllib.request
import urllib.error
import os
import sys
import unicodedata

MINIMUM_SIZE = 10
LOG_LEVEL = logging.INFO
LOG_FILE = 'download.log' or False
LOG_FORMAT = '%(asctime)s %(filename)s:%(lineno)d [%(levelname)s] %(message)s'


def set_logger():
    logger = logging.getLogger()
    logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if LOG_FILE:
        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(LOG_LEVEL)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


logger = set_logger()

logger.info("fetching msg from %s \n" % sys.argv[1])
url = re.sub("#/", "", sys.argv[1]).strip()
r = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36'})
contents = r.text
res = r'<ul class="f-hide">(.*?)</ul>'
mm = re.findall(res, contents, re.S | re.M)
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
if (mm):
    contents = mm[0]
else:
    logger.error('Can not fetch information form URL. Please make sure the URL is right.\n')
    os._exit(0)

res = r'<li><a .*?>(.*?)</a></li>'
mm = re.findall(res, contents, re.S | re.M)

for value in mm:
    url = 'http://sug.music.baidu.com/info/suggestion'
    payload = {'word': value, 'version': '2', 'from': '0'}
    value = value.replace('\\xa0', ' ')  # windows cmd 的编码问题
    logger.info(value)

    r = requests.get(url, params=payload)
    contents = r.text
    d = json.loads(contents, encoding="utf-8")
    if d is not None and 'data' not in d:
        continue
    songid = d["data"]["song"][0]["songid"]
    logger.info("find songid: %s" % songid)

    url = "http://music.baidu.com/data/music/fmlink"
    payload = {'songIds': songid, 'type': 'flac'}
    r = requests.get(url, params=payload)
    contents = r.text
    d = json.loads(contents, encoding="utf-8")
    if ('data' not in d) or d['data'] == '':
        continue
    songlink = d["data"]["songList"][0]["songLink"]
    logger.info("find songlink: ")
    if (len(songlink) < 10):
        logger.warning("\tdo not have flac\n")
        continue
    logger.info(songlink)

    songdir = "songs_dir"
    if not os.path.exists(songdir):
        os.makedirs(songdir)

    songname = d["data"]["songList"][0]["songName"]
    artistName = d["data"]["songList"][0]["artistName"]
    # trans chinese punctuation to english
    songname = unicodedata.normalize('NFKC', songname)
    songname = songname.replace('/', "%2F").replace('\"', "%22")
    # Replace the reserved characters in the song name to '-'
    songname = songname.replace('$', "-").replace('&', "-").replace('+', "-").replace(',', "-").replace(':',
                                                                                                        "-").replace(
        ';', "-").replace('=', "-").replace('?', "-").replace('@', "-")

    filename = ("%s/%s/%s-%s.flac" %
                (CURRENT_PATH, songdir, songname, artistName))

    f = urllib.request.urlopen(songlink)
    headers = requests.head(songlink).headers
    if 'Content-Length' in headers:
        size = round(int(headers['Content-Length']) / (1024 ** 2), 2)
    else:
        continue

    # Download unfinished Flacs again.
    if not os.path.isfile(filename) or os.path.getsize(filename) < MINIMUM_SIZE:  # Delete useless flacs
        logger.info("%s is downloading now ......\n\n" % songname)
        if size >= MINIMUM_SIZE:
            with open(filename, "wb") as code:
                code.write(f.read())
        else:
            logger.warning("the size of %s (%r Mb) is less than 10 Mb, skipping" %
                  (filename, size))
    else:
        logger.info("%s is already downloaded. Finding next song...\n\n" % songname)

logger.info("\n================================================================\n")
logger.info("Download finish!\nSongs' directory is %s/songs_dir" % os.getcwd())
