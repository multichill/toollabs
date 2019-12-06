#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Albright–Knox Art Gallery to Wikidata.

Just loop over pages like https://www.albrightknox.org/search-collection?field_culture_target_id[6]=6&page=1

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getGAlbrightKnoxGenerator():
    """
    Generator to return Albright–Knox Art Gallery paintings
    """
    basesearchurl = u'https://www.albrightknox.org/search-collection?field_culture_target_id[6]=6&page=%s'
    htmlparser = HTMLParser()

    # 1877 hits, 25 per page

    for i in range(0, 77):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workurlregex = u'\<a class\=\"link-whole-area\" href\=\"\/artworks\/([^\"]+)\"\>\<\/a\>'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            url = u'https://www.albrightknox.org/artworks/%s' % (match.group(1),)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)

            metadata['url'] = url

            metadata['collectionqid'] = u'Q1970945'
            metadata['collectionshort'] = u'Albright–Knox'
            metadata['locationqid'] = u'Q1970945'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            # Messy website, both inventory number and credit use the same class
            creditinvregex = u'\<p class\=\"credit\"\>([^\<]+)\<\/p\>[\r\n\t\s]*\<p class\=\"credit\"\>([^\<]+)\<\/p\>'
            creditinvmatch = re.search(creditinvregex, itempage.text)
            # Not sure if I need to replace space here
            metadata['id'] = htmlparser.unescape(creditinvmatch.group(2).replace(u'&nbsp;', u' ')).strip()

            # Do something with the credit year here

            acquisitiondateregex = u'^.*(\d\d\d\d)$'
            acquisitiondatematch = re.search(acquisitiondateregex, creditinvmatch.group(1))
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            titleyearregex = u'\<em class\=\'f-italic\'\>([^\<]+)\<\/em\>\<span class\=\'f-artwork-year\'\>,\s*([^\<]+)\<\/span\>'

            titleyearmatch = re.search(titleyearregex, itempage.text)

            if titleyearmatch:
                title = htmlparser.unescape(titleyearmatch.group(1)).strip()

                # Chop chop, several very long titles
                if len(title) > 220:
                    title = title[0:200]
                metadata['title'] = { u'en' : title,
                                      }

                # Let's see if we can extract some dates.

                inceptiontext = titleyearmatch.group(2).strip()

                dateregex = u'^\s*(\d\d\d\d)\s*$'
                datecircaregex = u'^\s*ca\.\s*(\d\d\d\d)\s*$'
                periodregex = u'^\s*(\d\d\d\d)-(\d\d\d\d)\s*$'
                circaperiodregex = u'^\s*ca\.\s*(\d\d\d\d)-(\d\d\d\d)\s*$'
                #shortperiodregex = u'\<meta content\=\"(\d\d)(\d\d)–(\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
                #circashortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d)(\d\d)–(\d\d)\<\/p\>'

                datematch = re.search(dateregex, inceptiontext)
                datecircamatch = re.search(datecircaregex, inceptiontext)
                periodmatch = re.search(periodregex, inceptiontext)
                circaperiodmatch = re.search(circaperiodregex, inceptiontext)
                shortperiodmatch = None
                circashortperiodmatch = None

                if datematch:
                    metadata['inception'] = int(datematch.group(1).strip())
                elif datecircamatch:
                    metadata['inception'] = int(datecircamatch.group(1).strip())
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1))
                    metadata['inceptionend'] = int(periodmatch.group(2))
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                    metadata['inceptionend'] = int(circaperiodmatch.group(2))
                    metadata['inceptioncirca'] = True
                elif shortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
                elif circashortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                    metadata['inceptioncirca'] = True
                else:
                    print (u'Could not parse date: "%s"' % (inceptiontext,))

            creatoregex = u'\<div class\=\"info-maker\"\>[\r\n\t\s]*\<h1\>\<a href\=\"[^\"]*\" hreflang\=\"en\"\>\s*([^\<]+)\s*\<\/a\>\<\/h1\>'
            creatormatch = re.search(creatoregex, itempage.text)

            # Rare cases without a match
            if creatormatch:
                creatorname = htmlparser.unescape(creatormatch.group(1)).strip()

                metadata['creatorname'] = creatorname

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                            u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                            }

            mediumregex = u'\<p class\=\"materials\"\>oil on canvas\<\/p\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            ## Dimensions are messy and in inches + cm, could have a shot at it later
            #measurementsregex = u'\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>Sight\:[^\<]+in\.\s*\(([^\(]+)\)\<\/div\>'
            #measurementsmatch = re.search(measurementsregex, itempage.text)
            #if measurementsmatch:
            #    measurementstext = measurementsmatch.group(1)
            #    regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*×\s*(?P<width>\d+(\.\d+)?)\s*cm$'
            #    match_2d = re.match(regex_2d, measurementstext)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
            #        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            # They offer tiff files!
            imageregex = u'\<a href\=\"(http[^\"]+\.tif)\" download class\=\"icon icon-download\"\>download\<\/a\>'
            imagematch = re.search(imageregex, itempage.text)
            if imagematch and u'<p class="copywrite">Public Domain </p>' in itempage.text:
                metadata[u'imageurl'] = htmlparser.unescape(imagematch.group(1))
                metadata[u'imageurlformat'] = u'Q215106' #TIFF
            #    metadata[u'imageurllicense'] = u'' # No license
                metadata[u'imageoperatedby'] = u'Q1970945'
            #    # Used this to add suggestions everywhere
            #    metadata[u'imageurlforce'] = True

            yield metadata


def main():
    dictGen = getGAlbrightKnoxGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
