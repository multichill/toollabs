#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Quick and dirty script to add sitters to https://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings/Collection/National_Portrait_Gallery,_London/Missing_sitter

"""
import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql
import requests
import re

def paintingGenerator():
    """
    Get the paintings to work on with extra metadata
    :return:
    """
    query = u"""SELECT ?item ?sitter ?sittername ?yob ?yod ?npgurl WHERE {
  wd:P6152 wdt:P1630 ?formatterurl .
  ?item p:P195/ps:P195 wd:Q238587 .
  ?item wdt:P136 wd:Q134307 .
  MINUS { ?item wdt:P921 [] } .
  ?item wdt:P31 wd:Q3305213 .
  ?item rdfs:label ?sittername .
  FILTER(LANG(?sittername)="en")
  { ?sitter rdfs:label ?sittername } UNION { ?sitter skos:altLabel ?sittername } .
  ?sitter wdt:P569 ?dob .
  BIND(YEAR(?dob) AS ?yob)  .
  OPTIONAL { ?sitter wdt:P570 ?dod . BIND(YEAR(?dod) AS ?yod) .} .
  ?sitter wikibase:sitelinks ?sitterlinks .
  ?item wdt:P973 ?npgurl .
} ORDER BY DESC(?sitterlinks) LIMIT 3000"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    repo = pywikibot.Site().data_repository()

    for resultitem in queryresult:
        info = {}
        info['item'] = pywikibot.ItemPage(repo, title=resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u''))
        info['sitter'] = pywikibot.ItemPage(repo, title=resultitem.get('sitter').replace(u'http://www.wikidata.org/entity/', u''))
        info['sittername'] = resultitem.get('sittername')
        info['yob'] = resultitem.get('yob')
        info['yod'] = resultitem.get('yod')
        info['npgurl'] = resultitem.get('npgurl')
        yield info

def addSitter(paintinginfo):
    """
    Add sitter to the item if possible

    :param paintinginfo: The relevant metadata, see above
    :return: Edit the item in place
    """
    repo = pywikibot.Site().data_repository()
    itempage = paintinginfo.get('item')
    data = itempage.get()
    claims = data.get('claims')

    if u'P921' in claims:
        return

    print (paintinginfo.get('npgurl'))
    npgpage = requests.get(paintinginfo.get('npgurl'))

    samepersonsummary = u''

    deathsitterregex = u'\<ul id\=\"sitter-list\"\>\<li\>\<a href\=\"[^\"]+\"\>[^\<]+\<\/a\>\s*\((\d\d\d\d)-(\d\d\d\d)\)[^\<]*\<\/li\>'
    livingsitterregex = u'\<ul id\=\"sitter-list\"\>\<li\>\<a href\=\"[^\"]+\"\>[^\<]+\<\/a\>\s*\((\d\d\d\d)-\)[^\<]*\<\/li\>'

    deathsittermatch = re.search(deathsitterregex, npgpage.text)
    livingsittermatch = re.search(livingsitterregex, npgpage.text)

    if paintinginfo.get('yob') and paintinginfo.get('yod') and deathsittermatch:
        if int(paintinginfo.get('yob')) == int(deathsittermatch.group(1)):
            if int(paintinginfo.get('yod')) == int(deathsittermatch.group(2)):
                samepersonsummary = u'based on label "%(sittername)s" and same year of birth (%(yob)s) and death (%(yod)s)' % paintinginfo
    elif paintinginfo.get('yob') and not paintinginfo.get('yod') and not deathsittermatch and livingsittermatch:
        if int(paintinginfo.get('yob')) == int(livingsittermatch.group(1)):
            samepersonsummary = u'based on label "%(sittername)s" and same year of birth (%(yob)s)' % paintinginfo

    if not samepersonsummary:
        return

    print (samepersonsummary)

    mainsubjectclaim = pywikibot.Claim(repo, u'P921')
    mainsubjectclaim.setTarget(paintinginfo.get('sitter'))
    itempage.addClaim(mainsubjectclaim, summary=samepersonsummary)

    if not u'P180' in claims:
        depictsclaim = pywikibot.Claim(repo, u'P180')
        depictsclaim.setTarget(paintinginfo.get('sitter'))
        itempage.addClaim(depictsclaim, summary=samepersonsummary)


def main(*args):
    """
    Main function. Grab a generator and process each item
    """
    generator = paintingGenerator()

    for paintinginfo in generator:
        print (paintinginfo)
        addSitter(paintinginfo)

if __name__ == "__main__":
    main()
