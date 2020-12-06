#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Crystal Bridges Museum of American Art to Wikidata.

Just loop over pages like https://collection.crystalbridges.org/advancedsearch/Objects/classifications%3APainting/images?page=2

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getCrystalBridgesGenerator():
    """
    Generator to return Crystal Bridges paintings
    """
    basesearchurl = 'https://collection.crystalbridges.org/advancedsearch/Objects/classifications%%3APainting/images?page=%s'
    htmlparser = HTMLParser()
    referer = 'https://collection.crystalbridges.org/advancedsearch/Objects/classifications%3APainting/images'

    # Stupid Emuseum junk
    session = requests.Session()
    session.get('https://collection.crystalbridges.org/collections')
    session.get('https://collection.crystalbridges.org/advancedsearch')

    # 456 hits, 24 per page.
    for i in range(1, 20):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        # Stupid website won't page without the extra headers
        searchPage = session.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                     'referer' : referer,}
                                 )

        workurlregex = '\<div class\=\"title text-wrap\"\>\<a class\=\"\" href\=\"\/objects\/(\d+)\/([^\?]+)\?[^\"]+\"\>([^\<]+)\<\/a\>\<\/div\>'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            metadata = {}
            pageid = match.group(1)
            slug = match.group(2)
            title = htmlparser.unescape(match.group(3)).strip()
            url = 'https://collection.crystalbridges.org/objects/%s/%s' % (pageid, slug,)

            itempage = session.get(url, headers={'referer' : referer,})
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q1142334'
            metadata['collectionshort'] = 'Crystal Bridges'
            metadata['locationqid'] = 'Q1142334'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = u'P217'

            invregex = '\<span class\=\"detailFieldLabel\"\>\<span\>Accession number\<\/span\>\<\/span\>\<span class\=\"detailFieldValue\"\>[\r\n\s\t]*([^\r\n\s\<]+)[\r\n\s\t]*\<\/span\>'
            invmatch = re.search(invregex, itempage.text)
            if invmatch:
                # These weird people don't assign inventory numbers to promised gifts.
                # Not sure if I need to replace space here
                metadata['id'] = htmlparser.unescape(invmatch.group(1).replace('&nbsp;', ' ')).strip()
            else:
                print('Unable to find accession number on %s' % (url,))
                # This sucks, but just too many
                metadata['id'] = 'promised_gift_%s_%s' % (pageid, slug,)

            # Already got it
            #titleregex = '\<meta property\=\"og\:title\" content\=\"([^\"]+)\"\s*\/\>'
            #titlematch = re.search(titleregex, itempage.text)
            #title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'en' : title,
                                  }

            creatorregex = '\<span property\=\"name\" itemprop\=\"name\"\>[\r\n\s\t]+([^\r\n\<]+)[\r\n\s\t]*\<\/span\>'
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
            dateregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)\<\/span\>'
            datecircaregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>ca?\.\s*(\d\d\d\d)\<\/span\>'
            periodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)\s*-\s*(\d\d\d\d)\<\/span\>'
            circaperiodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>ca?\.\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)\<\/span\>'
            shortperiodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d)(\d\d)-(\d\d)\<\/span\>'
            circashortperiodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>ca?\. (\d\d)(\d\d)-(\d\d)\<\/span\>'
            otherdateregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>'

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

            ## The accession number seems to contain the year. Let's extract that from the credit line
            acquisitiondateregex = '\<div class\=\"detailField creditlineField\"\>\<span class\=\"detailFieldLabel\"\>Credit Line\<\/span\>\<span class\=\"detailFieldValue\"\>[^\<]+,\s*(\d\d\d\d)\.\d+\<\/span\>\<\/div\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = '\<span property\=\"artMedium\" itemprop\=\"artMedium\" class\=\"detailFieldValue\"\>Oil on canvas\<\/span\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = 'oil on canvas'

            # Dimensions are a bit messy and in inches + cm
            measurementsregex = '\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Dimensions\<\/span\>\<span class\=\"detailFieldValue\"\>[^\<]+\(([^\<]+)\)\<'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = '^(?P<height>\d+(\.\d+)?)\s*[×x]\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group('width').replace(',', '.')

            # They provide images with "unrestricted" in the url. Good enough for me!
            imageregex = '\<div style\=\"[^\"]+\" class\=\"emuseum-img-wrap width-img-wrap\" data-mediatype-id\=\"\d*\"\>\<img src\=\"(\/internal\/media\/dispatcher\/\d+\/unrestricted)\"'
            imagematch = re.search(imageregex, itempage.text, re.IGNORECASE)
            if imagematch:
                recentinception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recentinception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recentinception = True
                if not recentinception:
                    metadata['imageurl'] = 'https://collection.crystalbridges.org%s' % (imagematch.group(1),)
                    metadata['imageurlformat'] = 'Q2195' #JPEG
                    #metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
                    metadata['imageoperatedby'] = 'Q1142334'
                    #Used this to add suggestions everywhere
                    metadata[u'imageurlforce'] = True

            yield metadata


def main():
    dictGen = getCrystalBridgesGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
