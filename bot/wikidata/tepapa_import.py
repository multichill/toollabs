#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Museum of New Zealand Te Papa Tongarewa (Q915603) to Wikidata.

Just loop over pages like http://collections.tepapa.govt.nz/Search/AdvancedSearchCH?cboCOSection=&txtCORegNo=&cboCOClassificationLetters=A&cboCOClassification=paintings&txtCOTitle=&cboCOMaker=&cboCORole=&cboCOProdPlace=&txtCOProdDate=&cboCOMaterialsLetters=A&cboCOMaterials=&cboCOTechniqueLetters=A&cboCOTechnique=&txtCODescription=&cboCOAssSubjects=&cboCOAssConcept=&cboCOAssPeriodStyle=&cboCOAssAssociationName=&cboCOAssAssociationCountry=&cboCOAssiwi=&searchPageType=CH

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getTePapaGenerator():
    """
    Generator to return Museum of New Zealand Te Papa Tongarewa paintings
    """

    htmlparser = HTMLParser.HTMLParser()

    count = 12
    basesearchurl = u'http://collections.tepapa.govt.nz/Search/GetObjectThumbnailsShowMoreForAdvanced/?scope=all&imagesOnly=False&downloadable=False&startIndex=%s&returnCount=%s&advanced=colClassification:"paintings"+colCollectionGroup:CH'

    for i in range(1, 1793, count):
        searchurl = basesearchurl % (i, count)
        searchPage = requests.get(searchurl)
        for iteminfo in searchPage.json():
            metadata = {}
            url = u'http://collections.tepapa.govt.nz%s' % (iteminfo.get('path'),)

            # Museum site probably doesn't like it when we go fast
            # time.sleep(5)
            pywikibot.output(url)

            metadata['url'] = url

            metadata['collectionqid'] = u'Q915603'
            metadata['collectionshort'] = u'Te Papa'
            metadata['locationqid'] = u'Q915603'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'


            title = iteminfo.get('title')


            # Chop chop, in case we have very long titles
            if title > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                    }
            name = iteminfo.get('colProProductionMakers')

            if not name:
                metadata['creatorqid'] = u'Q4233718'
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
            else:
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)
                metadata['creatorname'] = name

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                           }

            metadata['inception'] = iteminfo.get('colProProductionDates')

            metadata['idpid'] = u'P217'
            metadata['id'] = iteminfo.get('colRegistrationNumber')

            # Not everything is in json, so some good old parsing
            itempage = requests.get(url)

            mediumregex = u'\<td class\=\"heading\"\>Medium summary\<\/td\>[\s\t\r\n]*\<td\>oil on canvas\<\/td\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            dimensionsregex = u'\<td class\=\"heading\"\>Dimensions\<\/td\>[\s\t\r\n]*\<td\>[\s\t\r\n]*(Overall|Image):([^\<]+)[\s\t\r\n]*\<br \/\>'

            dimensionsmatch = re.search(dimensionsregex, itempage.text)

            if dimensionsmatch:
                dimensiontext = dimensionsmatch.group(2).strip()
                regex_2d = u'(?P<height>\d+)(mm)?\s*\(Height\)[\s\t\r\n]*x[\s\t\r\n]*(?P<width>\d+)(mm)?\s*\((Width|Length)\).*$'
                regex_3d = u'(?P<height>\d+)(mm)?\s*\(Height\)[\s\t\r\n]*x[\s\t\r\n]*(?P<width>\d+)(mm)?\s*\((Width|Length)\)[\s\t\r\n]*x[\s\t\r\n]*(?P<depth>\d+)(mm)?\s*\(Depth\).*$'
                match_2d = re.match(regex_2d, dimensiontext)
                match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = unicode(float(match_2d.group(u'height'))/10)
                    metadata['widthcm'] = unicode(float(match_2d.group(u'width'))/10)
                elif match_3d:
                    metadata['heightcm'] = unicode(float(match_3d.group(u'height'))/10)
                    metadata['widthcm'] = unicode(float(match_3d.group(u'width'))/10)
                    metadata['depthcm'] = unicode(float(match_3d.group(u'depth'))/10)

            creditlineregex = u'\<td class\=\"heading\"\>Credit line\<\/td\>[\s\t\r\n]*\<td\>([^\<]+ (?P<year1>\d\d\d\d)|Purchased (?P<year2>\d\d\d\d) [^\<]+)\<\/td\>'
            creditlinematch = re.search(creditlineregex, itempage.text)

            if creditlinematch:
                if creditlinematch.group(u'year1'):
                    metadata['acquisitiondate'] = creditlinematch.group(u'year1')
                elif creditlinematch.group(u'year2'):
                    metadata['acquisitiondate'] = creditlinematch.group(u'year2')

            yield metadata


def main():
    dictGen = getTePapaGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
