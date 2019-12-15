#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Seattle Art Museum to Wikidata.

Just loop over pages like http://art.seattleartmuseum.org/advancedsearch/objects/classifications%3APaintings/images?page=2

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getSeattleArtMuseumGenerator():
    """
    Generator to return Georgia Museum of Art paintings
    """
    basesearchurl = u'http://art.seattleartmuseum.org/advancedsearch/objects/classifications%%3APaintings/images?page=%s'
    htmlparser = HTMLParser()

    # 2218 hits, 36 per page

    for i in range(1, 63):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workidregex = u'\<h3 class\=\"[^\"]*\"\>\<a title\=\"[^\"]*\" href\=\"\/objects\/(\d+)\/'
        matches = re.finditer(workidregex, searchPage.text)

        for match in matches:
            url = u'http://art.seattleartmuseum.org/objects/%s/' % (match.group(1),)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)

            # Get url with slug
            urlregex = u'\<meta content\=\"([^\"]+)\;[^\"]+\" name\=\"og\:url\"\>'
            urlmatch = re.search(urlregex, itempage.text)

            if not urlmatch:
                print(u'Something went wrong. No url found. Sleeping and trying again')
                time.sleep(300)
                itempage = requests.get(url)
                urlmatch = re.search(urlregex, itempage.text)

            # they have a localhost bug here :-) No https
            ogurl = urlmatch.group(1).replace(u'http://localhost/objects/', u'http://art.seattleartmuseum.org/objects/')
            if ogurl.startswith(url):
                metadata['url'] = ogurl
            else:
                metadata['url'] = url

            metadata['collectionqid'] = u'Q1816301'
            metadata['collectionshort'] = u'Seattle'
            metadata['locationqid'] = u'Q1816301'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            invregex = u'\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            # Not sure if I need to replace space here
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace(u'&nbsp;', u' ')).strip()

            titleregex = u'\<meta content\=\"([^\"]+)\" name\=\"og\:title\"\>'
            titlematch = re.search(titleregex, itempage.text)

            title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            creatoregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema\:creator\" itemprop\=\"creator\"\>'
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


            # Let's see if we can extract some dates. Json-ld is provided, but doesn't have circa and the likes
            dateregex = u'\<meta content\=\"(\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            datecircaregex = u'\<meta content\=\"ca?\. (\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            periodregex = u'\<meta content\=\"(\d\d\d\d)-(\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            circaperiodregex = u'\<meta content\=\"ca?\. (\d\d\d\d)-(\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            shortperiodregex = u'\<meta content\=\"(\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            circashortperiodregex = u'\<meta content\=\"ca?\. (\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            otherdateregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'

            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            periodmatch = re.search(periodregex, itempage.text)
            circaperiodmatch = re.search(circaperiodregex, itempage.text)
            shortperiodmatch = re.search(shortperiodregex, itempage.text)
            circashortperiodmatch = re.search(circashortperiodregex, itempage.text)
            otherdatematch = re.search(otherdateregex, itempage.text)

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
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # Provenance is provided, sometimes has a date
            acquisitiondateregex = u'\<div class\=\"detailField provenanceField\"\>\<span class\=\"detailFieldLabel\"\>Provenance\: \<\/span\>\<span class\=\"detailFieldValue\"\>[^\<]+(\d\d\d\d)\<\/span\>\<\/div\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = u'\<meta content\=\"Oil on canvas\" property\=\"schema\:artMedium\" itemprop\=\"artMedium\"\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            ## Dimensions are messy and in inches + cm
            #measurementsregex = u'\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>Sight\:[^\<]+in\.\s*\(([^\(]+)\)\<\/div\>'
            #measurementsmatch = re.search(measurementsregex, itempage.text)
            #if measurementsmatch:
            #    measurementstext = measurementsmatch.group(1)
            #    regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*×\s*(?P<width>\d+(\.\d+)?)\s*cm$'
            #    match_2d = re.match(regex_2d, measurementstext)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
            #        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            ## Just tiny images and not clear if it's free
            #imageregex = u'\<meta property\=\"og:image\" content\=\"([^\"]+)\"\ \/\>'
            #imagematch = re.search(imageregex, itempage.text)
            #if imagematch and u'https://creativecommons.org/licenses/by-sa/4.0/' in itempage.text:
            #    metadata[u'imageurl'] = imagematch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            #    metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
            #    metadata[u'imageoperatedby'] = u'Q262234'
            #    # Used this to add suggestions everywhere
            #    #metadata[u'imageurlforce'] = True

            yield metadata


def main():
    dictGen = getSeattleArtMuseumGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
