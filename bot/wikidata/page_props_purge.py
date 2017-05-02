#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to purge Wikidata items that don't have all the properties set.

First run https://tools.wmflabs.org/multichill/queries/wikidata/no_pageprops.sql to produce the list to work on

The bot will purge the items in batches.
"""
import pywikibot
import requests
import re
import time

def getToPurgeGenerator():
    '''
    Generate the items to purge
    '''
    url = u'https://tools.wmflabs.org/multichill/queries/wikidata/no_pageprops.txt'
    repo = pywikibot.Site(u'wikidata', u'wikidata').data_repository()
    regex = u'^\*\s?\[\[(?P<title>[^\]]+)\]\]'

    noclaimPage = requests.get(url)

    for match in re.finditer(regex, noclaimPage.text, flags=re.M):
        yield pywikibot.ItemPage(repo, match.group("title"))


def main(*args):
    """
    Run the bot.
    """
    repo = pywikibot.Site(u'wikidata', u'wikidata').data_repository()

    topurgegen = getToPurgeGenerator()

    purgelist = []
    batchsize = 50
    batch = 0
    for itempage in topurgegen:
        purgelist.append(itempage)
        if len(purgelist) > batchsize:
            batch = batch + 1
            pywikibot.output(u'Purging %s items in batch %s ending at %s' % (batchsize, batch, itempage.title()))
            try:
                repo.purgepages(purgelist, forcelinkupdate=1)
                purgelist = []
            except pywikibot.data.api.APIError:
                pywikibot.output(u'Yah! Broke it again. Let\'s sleep for a minute')
                time.sleep(60)
    pywikibot.output(u'Purging last batch')
    repo.purgepages(purgelist, forcelinkupdate=1)

if __name__ == "__main__":
    main()