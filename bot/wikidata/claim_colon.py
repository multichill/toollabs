#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add claims to items that have sitelinks that contain a ':'.
Main usages is to add instance of Q4167836 to categories

Expects an up to date list at https://tools.wmflabs.org/multichill/queries2/wikidata/noclaims_colon_list.txt

"""
import pywikibot
from pywikibot import pagegenerators
import urllib2
import re
import time


def getNoclaimGenerator():
    '''
    Bla %02d
    '''
    url = u'https://tools.wmflabs.org/noclaims/queries/noclaims_colon_list.txt'
    repo = pywikibot.Site(u'wikidata', u'wikidata').data_repository()
    regex = u'^\*\[\[(?P<title>[^\]]+)\]\] - (?P<rest>.+)$'

    noclaimPage = urllib2.urlopen(url)
    noclaimData = unicode(noclaimPage.read(), u'utf-8')

    #print noclaimData[0:100]

    for match in re.finditer(regex, noclaimData, flags=re.M):
        yield pywikibot.ItemPage(repo, match.group("title"))



def main():
    #lang = u'en'

    #templates = getTemplateClaims(lang=lang)
    #print templates

    repo = pywikibot.Site(u'wikidata', u'wikidata').data_repository()

    namespaceclaims = { 4 : u'Q14204246', # Wikipedia
                        10 : u'Q11266439', # Template
                        14 : u'Q4167836', # Category
                        100 : u'Q4663903', # Portal
                        828 : u'Q15184295', # Module
                      }
    
    noclaimgen = pagegenerators.PreloadingItemGenerator(getNoclaimGenerator())

    #repo = pywikibot.Site().data_repository()
    #print templates.keys()

    for itempage in noclaimgen:
        pywikibot.output(itempage.title())
        if not itempage.exists():
            pywikibot.output(u'Deleted, skipping')
            continue            
        if itempage.isRedirectPage():
            pywikibot.output(u'Redirect, skipping')
            continue
        data = itempage.get()
        if u'P31' not in data.get('claims'):
            for page in itempage.iterlinks(family=u'wikipedia'):
                pywikibot.output(page.title())
                if not page.namespace()==0 and page.namespace() in namespaceclaims:
                    pywikibot.output(u'Working on %s' % (page.title(), ))
                    newclaim = pywikibot.Claim(repo, u'P31')
                    claimtarget = pywikibot.ItemPage(repo, namespaceclaims.get(page.namespace()))
                    newclaim.setTarget(claimtarget)
                    summary = u'Adding [[Property:%s]] -> [[%s]] based on %s' % (u'P31', namespaceclaims.get(page.namespace()), page.title(asLink=True))
                    pywikibot.output(summary)
                    try:
                        itempage.addClaim(newclaim, summary=summary)
                    except pywikibot.exceptions.APIError:
                        pywikibot.output(u'Ai, API problems. Let\'s sleep')
                        time.sleep(60)
                    break

if __name__ == "__main__":
    main()
