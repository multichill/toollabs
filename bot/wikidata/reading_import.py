#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Reading Public Museum to Wikidata.

Just loop over pages like collection.readingpublicmuseum.org/advancedsearch/objects/classifications%3APainting/images?page=2

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getRinglingGenerator():
    """
    Generator to return Reading paintings
    """
    basesearchurl = 'http://collection.readingpublicmuseum.org/advancedsearch/objects/classifications%%3APainting/images?page=%s'
    htmlparser = HTMLParser()

    # 775 hits, 36 per page

    for i in range(1, 23):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workurlregex = '\<div data-a2a-title\=\"[^\"]*\" data-a2a-url\=\"(http\:\/\/collection\.readingpublicmuseum\.org\/objects\/\d+/[^\"]+)\;jsessionid[^\"]*\"'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            url = match.group(1)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q7300542'
            metadata['collectionshort'] = 'Reading'
            metadata['locationqid'] = 'Q7300542'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            metadata['idpid'] = 'P217'


            invregex = u'\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldLabel\"\>Object number\:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            #if not invmatch:
            #    # Some pages are empty ( https://emuseum.ringling.org/emuseum/objects/21096/evening-street )
            #    print (u'No inventory number found')
            #    continue
            # Not sure if I need to replace space here
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace('&nbsp;', ' ')).strip()



            titleregex = u'\<meta content\=\"([^\"]+)\" name\=\"og\:title\"\>'
            titlematch = re.search(titleregex, itempage.text)

            title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            # In the embedded metadata they loose the circle of/follower of part
            #creator1regex = '\<span class\=\"detailFieldLabel\"\>Artist\:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>\<a href\=\"[^\"]+">([^\<]*[\s\t\r\n]*[^\<]+[\s\t\r\n]*)\<\/a\>'
            creator1regex = '\<span class\=\"detailFieldLabel\"\>Artist\:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>\<a href=\"[^\"]+\"\>\<span\>([^\<]+)\<\/span\>\<\/a\>'
            creator2regex = '\<meta content\=\"([^\"]+)\" property\=\"schema\:creator\" itemprop\=\"creator\"\>'

            creator1match = re.search(creator1regex, itempage.text)
            creator2match = re.search(creator2regex, itempage.text)

            creator1name = ''
            creator2name = ''

            if creator1match:
                creator1name = htmlparser.unescape(creator1match.group(1)).replace(u'\n', u' ').strip()
            if creator2match:
                creator2name = htmlparser.unescape(creator2match.group(1)).replace(u'\n', u' ').strip()

            if not creator1name and not creator2name:
                metadata['description'] = { 'en' : 'painting by anonymous painter', }
                metadata['creatorqid'] = 'Q4233718' # Completely anonymous

            if creator1name and creator2name and  creator1name!=creator2name:
                metadata['creatorqid'] = 'Q4233718' # Circle of/follower of, etc. anonymous

            # First creator name has all the nice details in it
            if creator1name:
                metadata['creatorname'] = creator1name

                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }



            # Let's see if we can extract some dates. Date in meta fields is provided
            dateregex = '\<meta content\=\"(\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            datecircaregex = '\<meta content\=\"ca?\.\s*(\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            periodregex = '\<meta content\=\"(\d\d\d\d)\s*-\s*(\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            circaperiodregex = '\<meta content\=\"ca?\.\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            shortperiodregex = '\<meta content\=\"(\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            circashortperiodregex = '\<meta content\=\"ca?\. (\d\d)(\d\d)-(\d\d)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'
            otherdateregex = '\<meta content\=\"([^\"]+)\" property\=\"schema\:dateCreated\" itemprop\=\"dateCreated\"\>'

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
                print ('Could not parse date: "%s"' % (otherdatematch.group(1),))

            ## Credit line is provided, sometimes has a date
            #acquisitiondateregex = u'\<div class\=\"detailField creditlineField\"\>\<span class\=\"detailFieldLabel\"\>Credit Line\:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>[^\<]+ (\d\d\d\d)\<\/span\>\<\/div\>'
            #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            #if acquisitiondatematch:
            #    metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = '\<meta content\=\"oil on canvas\" property\=\"schema\:artMedium\" itemprop\=\"artMedium\"\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = 'oil on canvas'

            # Thesaurus with terms. Look for some terms
            if '"/vocabularies/thesaurus/28973;' in itempage.text:
                metadata['genreqid'] = 'Q134307' # portrait
            elif '"/vocabularies/thesaurus/28970;' in itempage.text:
                metadata['genreqid'] = 'Q191163' # landscape art
            elif '"/vocabularies/thesaurus/28987;' in itempage.text:
                metadata['genreqid'] = 'Q170571' # still life
            elif '"/vocabularies/thesaurus/28978;' in itempage.text:
                metadata['genreqid'] = 'Q1047337' # genre art
            elif '"/vocabularies/thesaurus/28976;' in itempage.text:
                metadata['genreqid'] = 'Q158607' # marine art (seascape)
            elif '"/vocabularies/thesaurus/29354;' in itempage.text:
                metadata['genreqid'] = 'Q2864737' # religious art

            ## Dimensions are messy and in inches + cm
            # measurementsregex = u'\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\="detailFieldValue"><div>31 x 41 1/4 in. (78.7 x 104.8 cm)</div>'
            #measurementsmatch = re.search(measurementsregex, itempage.text)
            #if measurementsmatch:
            #    measurementstext = measurementsmatch.group(1)
            #    regex_2d = u'^(?P<height>\d+(\.\d+)?)\s*×\s*(?P<width>\d+(\.\d+)?)\s*cm$'
            #    match_2d = re.match(regex_2d, measurementstext)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
            #        metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            # They provide images and mention something about fair use non-commercial bla. Intent to share. Good enough
            #imageregex = '\<meta property\=\"og:image\" content\=\"([^\"]+)\"\ \/\>'
            imageregex = '\<meta content\=\"([^\"]+)\;jsessionid[^\"]*\" name\=\"og\:image\"\>'
            imagematch = re.search(imageregex, itempage.text)
            if imagematch:
                recentinception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recentinception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recentinception = True
                if not recentinception:
                    metadata['imageurl'] = imagematch.group(1)
                    metadata['imageurlformat'] = 'Q2195' #JPEG
                    #metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
                    metadata['imageoperatedby'] = 'Q7300542'
                    #Used this to add suggestions everywhere
                    #metadata[u'imageurlforce'] = True

            yield metadata


def main():
    dictGen = getRinglingGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
