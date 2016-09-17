#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Some records in the RKD artists database got deleted. This tool will deprecate these links in Wikidata

"""
import pywikibot
import re
import requests

def toDeprecateGenerator():
    '''
    Generate wikidata item id and rkd artists id tuples
    '''
    repo = pywikibot.Site().data_repository()
    pageTitle = u'User:Multichill/Zandbak'
    page = pywikibot.Page(repo, title=pageTitle)
    text = page.get()
    regex = u'^\* \[\[Q(?P<paintingitem>\d+)\]\] - (?P<rkdid>\d+)$'

    for match in re.finditer(regex, text, flags=re.M):
        paintingItem = pywikibot.ItemPage(repo, title=u'Q%s' % (match.group("paintingitem"),))
        yield (paintingItem, match.group("rkdid"))

def rkdDeprecate(paintingitem, rkdid):
    '''
    Look for the paintingitem and if it has the rkdid
    '''
    pywikibot.output(u'Working on item %s' % (paintingitem.title(),))
    rkdbaseurl = u'https://api.rkd.nl/api/record/artists/%s?format=json'
    #rkdbaseurl = u'http://api-rkd.picturae.pro/api/record/artists/%s?format=json'
    rkdbaseurl = u'https://rkd.nl/en/explore/artists/%s'
    
    if not paintingitem.exists():
        pywikibot.output(u'Item %s does not exist, skipping' % (paintingitem.title(),))
        return False
    if paintingitem.isRedirectPage():
        pywikibot.output(u'Item %s is a redirect, skipping' % (paintingitem.title(),))
        return False

    data = paintingitem.get()
    claims = data.get('claims')

    if not 'P650' in claims:
        pywikibot.output(u'Item %s does not have a RKDartists ID (P650) claim, skipping' % (paintingitem.title(),))
        return False

    rkdclaim = claims.get('P650')[0]
    rkdtarget = rkdclaim.getTarget()
    if not rkdtarget==rkdid:
        pywikibot.output(u'Item %s has %s as ID and trying to deprecate %s, skipping' % (paintingitem.title(),rkdtarget, rkdid))
        return False

    rkdurl = rkdbaseurl % (rkdid,)
    rkdPage = requests.get(rkdurl, verify=False) # SSL problem
    if not rkdPage.status_code==404:
        pywikibot.output(u'Item %s did not give a 404 for %s, the returned code was %s, skipping' % (paintingitem.title(), rkdid, rkdPage.status_code))
        return False

    rkdclaimrank = rkdclaim.getRank()
    print rkdclaimrank

    if rkdclaimrank==u'deprecated':
        pywikibot.output(u'Item %s already set to deprecated for %s. Done!' % (paintingitem.title(), rkdid))
        return False

    if rkdclaimrank==u'normal':
        summary = u'Marking the link as deprecated. Record was deleted in RKDartists'
        pywikibot.output(summary)
        rkdclaim.setRank(u'deprecated')
        paintingitem.site.save_claim(rkdclaim, summary=summary)

def main():
    for (paintingitem, rkdid) in toDeprecateGenerator():
        rkdDeprecate(paintingitem, rkdid)
    

if __name__ == "__main__":
    main()
