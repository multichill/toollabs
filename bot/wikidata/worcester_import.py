#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Worcester Art Museum to Wikidata.

Just loop over pages like https://worcester.emuseum.com/advancedsearch/Objects/classifications%3APaintings/list?page=2

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getWorcesterGenerator():
    """
    Generator to return Worcester Art Museum  paintings
    """
    basesearchurl = u'https://worcester.emuseum.com/advancedsearch/Objects/classifications%%3APaintings/list?page=%s'
    htmlparser = HTMLParser()

    # 1452 hits, 24 per page

    for i in range(1, 62):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl, verify=False)

        workidregex = u'\<h3\>\<a href\=\"\/objects\/(\d+)\/'
        matches = re.finditer(workidregex, searchPage.text)

        for match in matches:
            url = u'https://worcester.emuseum.com/objects/%s/' % (match.group(1),)
            metadata = {}

            itempage = requests.get(url, verify=False)
            pywikibot.output(url)

            # Get url with slug
            urlregex = u'\<meta content\=\"([^\"]+)\;[^\"]+\" name\=\"og\:url\"\>'
            urlmatch = re.search(urlregex, itempage.text)

            if not urlmatch:
                print(u'Something went wrong. No url found. Sleeping and trying again')
                time.sleep(300)
                itempage = requests.get(url)
                urlmatch = re.search(urlregex, itempage.text)
            metadata['url'] = urlmatch.group(1)

            metadata['collectionqid'] = u'Q847508'
            metadata['collectionshort'] = u'Worcester'
            metadata['locationqid'] = u'Q847508'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            invregex = u'\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldLabel\"\>Object Number\: \<\/span\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>\<\/div\>'
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
            creatorregex = u'\<span property\=\"name\" itemprop\=\"name\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/span\>'
            creatormatch = re.search(creatorregex, itempage.text)

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
            dateregex = u'\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)\<\/span\>'
            datecircaregex = u'\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>about (\d\d\d\d)\<\/span\>'
            periodregex = u'\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)[-–](\d\d\d\d)\<\/span\>'
            circaperiodregex = u'\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>about (\d\d\d\d)[-–](\d\d\d\d)\<\/span\>'
            shortperiodregex = u'\<meta content\=\"(\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>' # Not seen
            circashortperiodregex = u'\<meta content\=\"ca?\.\s*(\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>' # Not seen
            otherdateregex = u'\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>'

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

            # Credit line doesn't seem to contain a date
            #acquisitiondateregex = u'\<div class\=\"detailField creditlineField\"\>\<span class\=\"detailFieldLabel\"\>Credit Line\: \<\/span\>\<!--\<div t\:type\=\"relatedfield\" t\:module\=\"eognl\:module\" t\:name\=\"propertyName\" t\:value\=\"value\"\>--\>\<span class\=\"detailFieldValue\"\>[^\<]+(\d\d\d\d)\<\/span\>'
            #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            #if acquisitiondatematch:
            #    metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = u'\<div class\=\"detailField mediumField\"\>\<span class\=\"detailFieldLabel\"\>Medium\: \<\/span\>\<span property\=\"artMedium\" itemprop\=\"artMedium\" class\=\"detailFieldValue\"\>oil on canvas\<\/span\>\<\/div\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            # Dimensions
            measurementsregex = u'\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>(board|canvas|panel)?\:\s*(?P<dim>[^\<]+)\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(u'dim')
                regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*x\s*(?P<width>\d+(\.\d+)?)\s*cm'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            # Add genre
            keywordregex = u'\<a href\=\"\/vocabularies\/thesaurus\/(\d+)\;[^\"]+\"\>'
            keywordmatches = re.finditer(keywordregex, itempage.text)

            genres = { u'1545838' : u'Q134307', # Portrait
                       u'1546170' : u'Q2864737', # Religious art
                       }

            for keywordmatch in keywordmatches:
                keyid = keywordmatch.group(1)
                if keyid in genres:
                    metadata[u'genreqid'] = genres.get(keyid)

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
    dictGen = getWorcesterGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
