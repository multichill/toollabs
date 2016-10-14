#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Lakenhal to Wikidata.

Screen scraping from.

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser

def getLakenhalGenerator():
    """
    Generator to return Lakenhal Museum paintings
    """
    basesearchurl = u'http://www.lakenhal.nl/nl/zoeken/collectie?keywords_type=schilderij&page=%s&q=*'
    baseUrlnl = u'http://www.lakenhal.nl/nl/collectie/%s'
    #baseUrlen = u'http://www.lakenhal.nl/en/collection/%s'

    htmlparser = HTMLParser.HTMLParser()

    for i in range(1, 99):
        searchUrl = basesearchurl % (i, )
        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text

        searchRegex = u'\<a class=\"search-result-link\" data-role=\"search-result\" href\=\"\/nl\/collectie\/([^\"]+)\"\>'
        matches = re.finditer(searchRegex, searchPageData)
        for match in matches:
            metadata = {}

            metadata['collectionqid'] = u'Q2098586'
            metadata['collectionshort'] = u'Lakenhal'
            metadata['locationqid'] = u'Q2098586'
            metadata['instanceofqid'] = u'Q3305213'

            metadata['url'] = baseUrlnl % match.group(1)

            itemPage = requests.get(metadata['url'])
            itemPageData = itemPage.text

            fieldsregex = u'\<dt class=\"col l-eleven m-seven s-all\">([^\<]+)\<\/dt\>\<dd class\=\"col l-ten m-six s-all\"\>([^\<]+)</dd>'
            fieldmatches = re.finditer(fieldsregex, itemPageData)
            for fieldmatch in fieldmatches:
                fieldname = htmlparser.unescape(fieldmatch.group(1))
                fieldvalue = htmlparser.unescape(fieldmatch.group(2))

                if fieldname == u'Titel':
                    metadata['title'] = { u'nl' : fieldvalue,
                                          }
                elif fieldname == u'Inventarisnummer':
                    metadata['idpid'] = u'P217'
                    metadata['id'] = fieldvalue
                elif fieldname == u'Maker':
                    metadata['creatorname'] = fieldvalue
                    metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                                u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
                elif fieldname == u'Datering':
                    metadata['inception'] = fieldvalue
                elif fieldname == u'Datum':
                    metadata['acquisitiondate'] = fieldvalue

                    #else:
                    # When it entered the collection
                elif fieldname == u'Materialen':
                    if fieldvalue == u'doek, olieverf':
                        metadata['medium'] = u'oil on canvas'
            yield metadata

    return
    
def main():
    dictGen = getLakenhalGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
