#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Isabella Stewart Gardner Museum to Wikidata.

Just loop over pages like https://www.gardnermuseum.org/experience/collection?ca=147&h=all&page=1

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getGardnerGenerator():
    """
    Generator to return Gardner paintings
    """
    basesearchurl = 'https://www.gardnermuseum.org/experience/collection?ca=147&h=all&page=%s'
    htmlparser = HTMLParser()

    # 417 hits, 9 per page. They start at zero
    for i in range(0, 47):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workurlregex = '\<h4 class\=\"piece__pre-title\"\>[\r\n\s\t]*([^\<]+)[\r\n\s\t]*\<\/h4\>[\r\n\s\t]*\<h3 class\=\"piece__title\"\>[\r\n\s\t]*\<a href\=\"\/experience\/collection\/(\d+)\"\>'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            creatorname = htmlparser.unescape(match.group(1)).strip()
            url = 'https://www.gardnermuseum.org/experience/collection/%s' % (match.group(2),)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q49135'
            metadata['collectionshort'] = 'Gardner'
            metadata['locationqid'] = 'Q49135'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = u'P217'

            invregex = '\<h2\>Accession number\<\/h2\>[\r\n\s\t]*\<p\>([^\<]+)\<\/p\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = htmlparser.unescape(invmatch.group(1)).strip()

            titleregex = '\<meta property\=\"og\:title\" content\=\"([^\"]+)\"\s*\/\>'
            titlematch = re.search(titleregex, itempage.text)

            title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            metadata['creatorname'] = creatorname
            metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                        'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                        'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                        'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                        }

            # Let's see if we can extract some dates. Date in meta fields is provided
            dateregex = '\<h1 class\=\"title-card__title\"\>[^\<]+,\s*(\d\d\d\d)\<\/h1\>'
            datecircaregex = '\<h1 class\=\"title-card__title\"\>[^\<]+,\s*about (\d\d\d\d)\<\/h1\>'
            periodregex = '\<h1 class\=\"title-card__title\"\>[^\<]+,\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)\<\/h1\>'
            circaperiodregex = '\<h1 class\=\"title-card__title\"\>[^\<]+,\s*about (\d\d\d\d)\s*-\s*(\d\d\d\d)\<\/h1\>'
            shortperiodregex = '\<h1 class\=\"title-card__title\"\>[^\<]+,\s*(\d\d)(\d\d)-(\d\d)\<\/h1\>' # Not seen
            circashortperiodregex = '\<h1 class\=\"title-card__title\"\>[^\<]+,\s*about (\d\d)(\d\d)-(\d\d)\<\/h1\>' # Not seen
            otherdateregex = '\<h1 class\=\"title-card__title\"\>[^\<]+,\s*([^\<]+)\<\/h1\>'

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
                metadata['inceptionstart'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circashortperiodmatch:
                metadata['inceptionstart'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print ('Could not parse date: "%s"' % (otherdatematch.group(1),))

            ## Credit line is too difficult to parse
            #acquisitiondateregex = u'\<div class\=\"detailField creditlineField\"\>\<span class\=\"detailFieldLabel\"\>Credit Line\:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>[^\<]+ (\d\d\d\d)\<\/span\>\<\/div\>'
            #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            #if acquisitiondatematch:
            #    metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = '\<div class\=\"title-card__content-block\"\>[\r\n\s\t]+\<div class\=\"title-card__text\"\>[\r\n\s\t]+\<p\>Oil on canvas,'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = 'oil on canvas'

            ## Dimensions are messy and in inches + cm
            measurementsregex = '\<div class\=\"title-card__content-block\"\>[\r\n\s\t]+\<div class\=\"title-card__text\"\>[\r\n\s\t]+\<p\>[^,]+,\s*([^\<]+cm)'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = '^(?P<height>\d+(\.\d+)?)\s*[×x]\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group('width').replace(',', '.')

            # They provide images under cc-by-nc-4.0. Good enough for me. Just take the first one
            imageregex = '\<a class\=\"header-thumbnail-carousel__item has-background-image\" href\=\"(https\:\/\/www\.gardnermuseum\.org\/sites\/default\/files\/images\/art\/[^\"]+\.jpg)\" target=\"_blank\"\>'
            imagematch = re.search(imageregex, itempage.text, re.IGNORECASE)
            if imagematch:
                metadata['imageurl'] = imagematch.group(1)
                metadata['imageurlformat'] = 'Q2195' #JPEG
            #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                metadata['imageoperatedby'] = 'Q49135'
                # Used this to add suggestions everywhere
                metadata['imageurlforce'] = True

            yield metadata


def main():
    dictGen = getGardnerGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
