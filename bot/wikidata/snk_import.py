#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Stichting Nederlands Kunstbezit (Q28045665) to Wikidata.

Just loop over pages like http://herkomstgezocht.nl/nl/search/collection?page=1&f[0]=type%3Ank_record&f[1]=field_objectaanduiding%3A11621

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getSNKGenerator():
    """
    Generator to return  Stichting Nederlands Kunstbezit paintings
    """
    basesearchurl = u'http://herkomstgezocht.nl/nl/search/collection?f[0]=type%%3Ank_record&f[1]=field_objectaanduiding%%3A11621&page=%s'
    htmlparser = HTMLParser.HTMLParser()

    # 1614 results, 15 per page (starting at 0)
    for i in range(0, 108):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        #urlregex = u'\<a href\=\"(\/art\/detail\/\d+)\?returnUrl\=[^\"]+\"\>[^\<]+\<\/a\>'
        urlregex = u'\<a class\=\"read-more\" href\=\"(http\:\/\/herkomstgezocht\.nl\/nl\/nk-collectie\/[^\"]+)\"\>read more\<\/a\>'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = match.group(1)

            # Museum site probably doesn't like it when we go fast
            # time.sleep(5)

            pywikibot.output(url)

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q28045665'
            metadata['collectionshort'] = u'SNK'
            # No location, it's a meta collection
            # metadata['locationqid'] = u'Q238587'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Let's see if this one works or if we have to make it a bit more liberal
            invregex = u'\<div class\=\"field field-name-field-icn-inventarisnummer\"\>(NK\d+[^\<]*)\<\/div\>'
            invmatch = re.search(invregex, itempage.text)

            metadata['idpid'] = u'P217'
            metadata['id'] = invmatch.group(1).strip()

            titleregex = u'\<div class\=\"field field-name-title-field\"\>\<h1\>([^\<]+)\<\/h1\>'
            titlematch = re.search(titleregex, itempage.text)

            title = htmlparser.unescape(titlematch.group(1).strip())

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'nl' : title,
                                  }
            creatorregex = u'\<div class\=\"field field-name-field-kunstenaar-tax field-type-taxonomy-term-reference field-label-hidden\"\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>([^\<]+)\<\/div\>'
            creatormatch = re.search(creatorregex, itempage.text)
            if creatormatch:
                name = htmlparser.unescape(creatormatch.group(1).strip())
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)

            # Works after/copy/etc.
            typeringregex = u'\<div class\=\"field field-name-field-typering field-type-taxonomy-term-reference field-label-hidden\"\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>([^\<]+)\<\/div\>'
            typeringmatch = re.search(typeringregex, itempage.text)

            if not creatormatch:
                metadata['creatorname'] = u'unknown artist'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            elif typeringmatch:
                typering = typeringmatch.group(1)
                metadata['creatorname'] = u'unknown artist'
                metadata['description'] = { u'nl' : u'schilderij %s %s' % (typering, name),
                                            }
                metadata['creatorqid'] = u'Q4233718'
            else:
                metadata['creatorname'] = name
                metadata['description'] = { u'en' : u'painting by %s' % (name, ),
                                            u'nl' : u'schilderij van %s' % (name, ),
                                            }
            # Old works, dating are rarely years
            # metadata['inception'] = datematch.group(1)

            # No date known, most of it will be 1946. Or should I use the "aangifte"? Not sure
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)


            oiloncanvasregex = u'\<div class\=\"field field-name-field-materiaal-techniek\"\>olieverf op doek\<\/div\>'
            oiloncanvasmatch = re.search(oiloncanvasregex, itempage.text)

            if oiloncanvasmatch:
                metadata['medium'] = u'oil on canvas'

            heightregex = u'\<div class=\"field field-name-field-hoogte-lengte\"\>(\d+\.\d+)\<\/div\>'
            heightmatch = re.search(heightregex, itempage.text)
            if heightmatch:
                metadata['heightcm'] = heightmatch.group(1).strip()

            widthregex = u'\<div class=\"field field-name-field-breedte\"\>(\d+\.\d+)\<\/div\>'
            widthmatch = re.search(widthregex, itempage.text)
            if widthmatch:
                metadata['widthcm'] = widthmatch.group(1).strip()

            yield metadata


def main():
    dictGen = getSNKGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
