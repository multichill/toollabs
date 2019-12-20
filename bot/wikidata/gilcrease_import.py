#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Gilcrease Museum to Wikidata.

Just loop over pages like https://collections.gilcrease.org/search/site?page=1&f%5B0%5D=im_field_classification%3A1045

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getGilcreaseGenerator():
    """
    Generator to return Gilcrease Museum  paintings
    """
    basesearchurl = u'https://collections.gilcrease.org/search/site?page=%s&f%%5B0%%5D=im_field_classification%%3A1045'
    htmlparser = HTMLParser()

    # 2307 hits, 20 per page

    for i in range(0, 116):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workidregex = u'\<a href\=\"https\:\/\/collections\.gilcrease\.org\/object\/(\d+)\"'
        matches = re.finditer(workidregex, searchPage.text)

        for match in matches:
            url = u'https://collections.gilcrease.org/object/%s' % (match.group(1),)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)

            metadata['url'] = url

            metadata['collectionqid'] = u'Q14708424'
            metadata['collectionshort'] = u'Gilcrease'
            metadata['locationqid'] = u'Q14708424'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            invregex = u'\<div class\=\"field-label\"\>Accession No\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>([^\<]+)\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            # Not sure if I need to replace space here
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace(u'&nbsp;', u' ')).strip()

            titleregex = u'\<div class\=\"field-label\"\>Title\(s\)\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\><div class\=\"field-item even\"\>([^\<]+)\<\/div\>'
            titlematch = re.search(titleregex, itempage.text)

            title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            creatorregex = u'\<div class\=\"field-label\"\>Creator\(s\)\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>([^\<]+)\<\/div\>'
            creatormatch = re.search(creatorregex, itempage.text)

            # Rare cases without a match
            if creatormatch or True:
                creatorname = htmlparser.unescape(creatormatch.group(1)).strip()

                metadata['creatorname'] = creatorname

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                            u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                            }

            # Let's see if we can extract some dates.
            dateregex = u'\<div class\=\"field-label\"\>Date\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>(\d\d\d\d)\<\/div\>'
            datecircaregex = u'\<div class\=\"field-label\"\>Date\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>circa (\d\d\d\d)\<\/div\>'
            periodregex = u'\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)[-–](\d\d\d\d)\<\/span\>' # Not seen
            circaperiodregex = u'\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>about (\d\d\d\d)[-–](\d\d\d\d)\<\/span\>' # Not seen
            shortperiodregex = u'\<meta content\=\"(\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>' # Not seen
            circashortperiodregex = u'\<meta content\=\"ca?\.\s*(\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>' # Not seen
            otherdateregex = u'\<div class\=\"field-label\"\>Date\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>([^\<]+)\<\/div\>'

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

            # Credit line sometimes contains a date
            acquisitiondateregex = u'\<div class\=\"field-label\"\>Credit Line\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>[^\<]+ (\d\d\d\d)\\<\/div\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = u'\<div class\=\"field-label\"\>Materials\/Techniques\:&nbsp\;\<\/div\>\<div class\=\"field-items\"\><div class\=\"field-item even\"\>oil on canvas\<\/div\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            # Dimensions is a pain to parse
            #measurementsregex = u'\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>(board|canvas|panel)?\:\s*(?P<dim>[^\<]+)\<\/div\>'
            #measurementsmatch = re.search(measurementsregex, itempage.text)
            #if measurementsmatch:
            #    measurementstext = measurementsmatch.group(u'dim')
            #    regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*x\s*(?P<width>\d+(\.\d+)?)\s*cm'
            #    match_2d = re.match(regex_2d, measurementstext)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
            #        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            # Add genre portrait. Tagging so other things don't seem to be very good quality
            portraitregex = u'\<a href\=\"\/tags\/portraits\"\>portraits?\<\/a\>'
            portraitmatch = re.search(portraitregex, itempage.text)
            if portraitmatch:
                metadata[u'genreqid'] = u'Q134307'

            ## NO free images
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
    dictGen = getGilcreaseGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
