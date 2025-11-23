#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Some records in the Rijksmonumenten database got deleted. These items have already been tagged with end dates.
This tool will deprecate these links in Wikidata

"""
import pywikibot
import re
import requests

def to_deprecate_generator():
    """
    Generate wikidata item id and rkd artists id tuples
    """
    repo = pywikibot.Site().data_repository()
    pageTitle = 'User:Multichill/Zandbak'
    page = pywikibot.Page(repo, title=pageTitle)
    text = page.get()
    regex = '^\* (?P<id>\d+) - \{\{Q\|(?P<item>Q\d+)\}\} .*$'

    for match in re.finditer(regex, text, flags=re.M):
        item = pywikibot.ItemPage(repo, title=match.group("item"))
        yield (item, match.group("id"))

def rijksmonument_deprecate(item, rijksmonument_id):
    """
    Update items that are no longer a Rijksmonument
    :param item:
    :param rijksmonument_id:
    :return:
    """
    pywikibot.output(u'Working on item %s' % (item.title(),))

    if not item.exists():
        pywikibot.output('Item %s does not exist, skipping' % (item.title(),))
        return False
    if item.isRedirectPage():
        pywikibot.output('Item %s is a redirect, skipping' % (item.title(),))
        return False

    data = item.get()
    claims = data.get('claims')

    if not 'P359' in claims:
        pywikibot.output('Item %s does not have a Rijksmonument ID (P359) claim, skipping' % (item.title(),))
        return False

    # Can only work on one to deprecate
    if not len(claims.get('P359')) == 1:
        pywikibot.output('Item %s has %s Rijksmonument ID (P359) claims, skipping' % (item.title(),
                                                                                      len(claims.get('P359')) ))
        return False

    if not 'P1435' in claims:
        pywikibot.output('Item %s does not have a heritage designation (P1435) claim, skipping' % (item.title(),))
        return False

    # Need the old rijksmonument claim and another no value claim
    if not len(claims.get('P1435')) == 2:
        pywikibot.output('Item %s has %s heritage designation (P1435) claims, skipping' % (item.title(),
                                                                                           len(claims.get('P1435')) ))
        return False

    rijksmonument_id_claim = claims.get('P359')[0]
    rm_qualifier_set = set(list(rijksmonument_id_claim.qualifiers.keys()))
    if rm_qualifier_set != {'P2241', 'P580', 'P582'}:
        pywikibot.output('Item %s has incorrect Rijksmonument ID (P359) qualifiers: %s, skipping' % (item.title(),
                                                                                                     rm_qualifier_set))
        return False

    heritage_designation_claim = claims.get('P1435')[1]

    if heritage_designation_claim.getSnakType() != 'novalue':
        pywikibot.output('Item %s has incorrect heritage designation (P1435) type, skipping' % (item.title(),))
        return False

    heritage_qualifier_set = set(list(heritage_designation_claim.qualifiers.keys()))
    if heritage_qualifier_set != {'P580'}:
        pywikibot.output('Item %s has incorrect heritage designation (P1435) qualifiers: %s, skipping' % (item.title(),
                                                                                                          heritage_qualifier_set))
        return False

    if rijksmonument_id_claim.getRank() == 'deprecated' and heritage_designation_claim.getRank() == 'preferred':
        pywikibot.output('Item %s already has the correct ranks. All done' % (item.title(),))
        return True

    if rijksmonument_id_claim.getRank() == 'normal':
        summary = 'marking ID as deprecated. No longer a Rijksmonument based on this ID.'
        pywikibot.output(summary)
        rijksmonument_id_claim.setRank('deprecated')
        item.site.save_claim(rijksmonument_id_claim, summary=summary)

    if heritage_designation_claim.getRank() == 'normal':
        summary = 'marking no value as preferred. No longer a Rijksmonument.'
        pywikibot.output(summary)
        heritage_designation_claim.setRank('preferred')
        item.site.save_claim(heritage_designation_claim, summary=summary)

    #print(rijksmonument_id_claim.getRank())
    #print(heritage_designation_claim.getRank())

    #if rijksmonument_id_claim.getRank()

    #print (claims.get('P359')[0].qualifiers)
    #print (claims.get('P1435')[0].qualifiers)
    return


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
    #print rkdclaimrank

    if rkdclaimrank==u'deprecated':
        pywikibot.output(u'Item %s already set to deprecated for %s. Done!' % (paintingitem.title(), rkdid))
        return False

    if rkdclaimrank==u'normal':
        summary = u'Marking the link as deprecated. Record was deleted in RKDartists'
        pywikibot.output(summary)
        rkdclaim.setRank(u'deprecated')
        paintingitem.site.save_claim(rkdclaim, summary=summary)

def main():
    for (item, rijksmonument_id) in to_deprecate_generator():
        rijksmonument_deprecate(item, rijksmonument_id)

    

if __name__ == "__main__":
    main()
