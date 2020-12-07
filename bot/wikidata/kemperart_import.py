#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Mildred Lane Kemper Art Museum to Wikidata.

Just loop over pages like https://www.kemperartmuseum.wustl.edu/collection/explore/medium/Paintings?page=1

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getKemperArtGenerator():
    """
    Generator to return Kemper Art paintings
    """
    basesearchurl = 'https://www.kemperartmuseum.wustl.edu/collection/explore/medium/Paintings?page=%s'
    htmlparser = HTMLParser()

    session = requests.Session()

    # 346 hits, 20 per page.
    for i in range(0, 18):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = session.get(searchurl)

        workurlregex = '\<span class\=\"field-content\"\>\<a href\=\"(\/collection\/explore\/artwork\/\d+)\"\>([^\<]+)\<\/a\>\<\/span\>'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            metadata = {}
            url = 'https://www.kemperartmuseum.wustl.edu%s' % (match.group(1),)
            title = htmlparser.unescape(match.group(2)).strip()

            itempage = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q6129019'
            metadata['collectionshort'] = 'Kemper Art'
            metadata['locationqid'] = 'Q6129019'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            invregex = '\<div class\=\"views-field-obj-identnr-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>([^\<]+)\<' # Broken html here
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace('&nbsp;', ' ')).strip()

            # Already got it
            #titleregex = '\<meta property\=\"og\:title\" content\=\"([^\"]+)\"\s*\/\>'
            #titlematch = re.search(titleregex, itempage.text)
            #title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'en' : title,
                                  }

            creatorregex = '\<div class\=\"artist-right\"\>\<strong\>\<a href\=\"[^\"]*\"\>([^\<]+)\<\/a\>\<\/strong\>'
            creatormatch = re.search(creatorregex, itempage.text)
            if creatormatch:
                creatorname = htmlparser.unescape(creatormatch.group(1)).strip()

                metadata['creatorname'] = creatorname
                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }

            # Quick and dirty, seems to catch most of it.
            dateregex = '\<div class\=\"views-field-obj-dating-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>(\d\d\d\d)\<\/span\>'
            datecircaregex = '\<div class\=\"views-field-obj-dating-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>ca?\.\s*(\d\d\d\d)\<\/span\>'
            periodregex = '\<div class\=\"views-field-obj-dating-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>(\d\d\d\d)\s*-\s*(\d\d\d\d)\<\/span\>'
            circaperiodregex = '\<div class\=\"views-field-obj-dating-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>ca?\.\s*(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)\<\/span\>'
            shortperiodregex = '\<div class\=\"views-field-obj-dating-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>(\d\d)(\d\d)\s*[–-]\s*(\d\d)\<\/span\>'
            circashortperiodregex = '\<div class\=\"views-field-obj-dating-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>ca?\. (\d\d)(\d\d)\s*[–-]\s*(\d\d)\<\/span\>'
            otherdateregex = '\<div class\=\"views-field-obj-dating-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>([^\<]+)\<\/span\>'

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

            ## The credit line has the year in it
            acquisitiondateregex = '\<div class\=\"views-field-obj-creditline-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>[^\<]+,\s*(\d\d\d\d)\<\/span\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = '\<div class\=\"views-field-obj-material-s\"\>[\r\n\s\t]*\<span class\=\"field-content\"\>Oil on canvas\<\/span\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = 'oil on canvas'

            # Dimensions are in Inches. I don't do Inches
            #measurementsregex = '\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Dimensions\<\/span\>\<span class\=\"detailFieldValue\"\>[^\<]+\(([^\<]+)\)\<'
            #measurementsmatch = re.search(measurementsregex, itempage.text)
            #if measurementsmatch:
            #    measurementstext = measurementsmatch.group(1)
            #    regex_2d = '^(?P<height>\d+(\.\d+)?)\s*[×x]\s*(?P<width>\d+(\.\d+)?)\s*cm$'
            #    match_2d = re.match(regex_2d, measurementstext)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group('height').replace(',', '.')
            #        metadata['widthcm'] = match_2d.group('width').replace(',', '.')

            # No free images
            #imageregex = '\<div style\=\"[^\"]+\" class\=\"emuseum-img-wrap width-img-wrap\" data-mediatype-id\=\"\d*\"\>\<img src\=\"(\/internal\/media\/dispatcher\/\d+\/unrestricted)\"'
            #imagematch = re.search(imageregex, itempage.text, re.IGNORECASE)
            #if imagematch:
            #    recentinception = False
            #    if metadata.get('inception') and metadata.get('inception') > 1924:
            #        recentinception = True
            #    if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
            #        recentinception = True
            #    if not recentinception:
            #        metadata['imageurl'] = 'https://collection.crystalbridges.org%s' % (imagematch.group(1),)
            #        metadata['imageurlformat'] = 'Q2195' #JPEG
            #        #metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
            #        metadata['imageoperatedby'] = 'Q1142334'
            #        #Used this to add suggestions everywhere
            #        metadata[u'imageurlforce'] = True

            yield metadata


def main():
    dictGen = getKemperArtGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
