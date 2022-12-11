#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Louvre to Wikidata.

The ark website at https://collections.louvre.fr/recherche?page=4&nCategory%5B0%5D=40&collection%5B0%5D=6 returns
a bit over 10.000 paintings from the Département des Peintures

For each entry they have json documented at https://collections.louvre.fr/en/page/documentationJSON

The paintings are all over France so adding that where possible

Use artdatabot to upload it to Wikidata
"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import datetime


def fix_louvre_inv(item):
    """
    Fix the Louvre inventory number for the item
    :param item:
    :return:
    """
    claims = item.get().get('claims')
    repo = item.site
    collection_item = pywikibot.ItemPage(repo, title='Q3044768')

    pywikibot.output('Working on %s' % (item,))

    if 'P9394' not in claims or len(claims.get('P9394')) != 1:
        return

    ark_id = claims.get('P9394')[0].getTarget()
    ark_url = 'https://collections.louvre.fr/ark:/53355/cl%s' % (ark_id, )
    ark_url_json = 'https://collections.louvre.fr/ark:/53355/cl%s.json' % (ark_id, )
    pywikibot.output(ark_url)
    item_json = requests.get(ark_url_json).json()

    if item_json.get('collection') != 'Département des Peintures':
        pywikibot.output('Not in Département des Peintures')
        return

    if item_json.get('objectNumber')[0].get('type') == 'Numéro principal':
        inv = item_json.get('objectNumber')[0].get('value')
    else:
        pywikibot.output('ID FAILED, skipping this one for now')
        pywikibot.output(item_json.get('objectNumber'))
        return

    for inv_statement in claims.get('P217'):
        if inv_statement.getTarget() == inv:
            if inv_statement.qualifiers.get('P195'):
                if inv_statement.qualifiers.get('P195')[0].getTarget().title() == 'Q3044768':
                    pywikibot.output('Found "%s". Nothing to do' % (inv,))
                    return
                elif len(inv_statement.qualifiers.get('P195'))==2 and \
                        inv_statement.qualifiers.get('P195')[0].getTarget().title() == 'Q19013512' and \
                        inv_statement.qualifiers.get('P195')[1].getTarget().title() == 'Q3044768':
                    inv_statement.removeQualifier(inv_statement.qualifiers.get('P195')[1])

    newclaim = pywikibot.Claim(repo, 'P217')
    newclaim.setTarget(inv)

    newqualifier = pywikibot.Claim(repo, 'P195')
    newqualifier.setTarget(collection_item)
    newclaim.addQualifier(newqualifier)

    refurl = pywikibot.Claim(repo, u'P854')
    refurl.setTarget(ark_url)
    refdate = pywikibot.Claim(repo, 'P813')
    today = datetime.datetime.today()
    date = pywikibot.WbTime(year=today.year, month=today.month, day=today.day)
    refdate.setTarget(date)

    newclaim.addSources([refurl, refdate])
    summary = 'adding missing (slightly different than Joconde) inventory number from Louvre ARK'
    pywikibot.output(summary)
    item.addClaim(newclaim, summary=summary)


def main(*args):
    repo = pywikibot.Site().data_repository()
    query = """SELECT ?item WHERE {
  ?item wdt:P9394 ?value ;
          wdt:P31 wd:Q3305213 ;
          p:P195/ps:P195 wd:Q3044768 .
  }
LIMIT 15000"""

    generator = pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=repo))

    for item in generator:
        fix_louvre_inv(item)

if __name__ == "__main__":
    main()
