#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the New-York Historical Society to Wikidata.

Just loop over pages https://emuseum.nyhistory.org/objects/images?filter=classifications%3APAINTINGS&page=2

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getNYhistoryGenerator():
    """
    Generator to return New-York Historical Society paintings
    """
    basesearchurl = 'https://emuseum.nyhistory.org/objects/images?filter=classifications%%3APAINTINGS&page=%s'
    htmlparser = HTMLParser()

    # Not sure if this needed for this Emuseum instance
    session = requests.Session()
    session.get('https://emuseum.nyhistory.org/objects')

    # 2564 hits, 36 per page.
    for i in range(1, 73):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = session.get(searchurl)

        workurlregex = '\<div class\=\"title text-wrap\"\>\<a class\=\"\"\s*href\=\"(\/objects\/\d+\/[^\?]+)\?[^\"]+\"\>'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            metadata = {}
            title = htmlparser.unescape(match.group(1)).strip()
            url = 'https://emuseum.nyhistory.org%s' % (match.group(1),)

            itempage = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q1059456'
            metadata['collectionshort'] = 'NYHS'
            metadata['locationqid'] = 'Q1059456'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            invregex = '\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>'
            invmatch = re.search(invregex, itempage.text)

            #if not invmatch:
            #    # Painting from a different collection
            #    continue
            # Not sure if I need to replace space here
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace('&nbsp;', ' ')).strip()

            titleregex = '\<meta content\=\"([^\"]+)\"\s*property\=\"og\:title\"\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            title = title.replace('\t', '').replace('\n', '')
            metadata['title'] = { 'en' : title,
                                  }
            creatorregex = '\<span class\=\"detailFieldLabel\"\>Artist\/Maker\<\/span\>\<span class\=\"detailFieldValue\"\>\<a property\=\"url\" itemprop\=\"url\" href\=\"\/people\/(\d+)\/[^\"]+\"\>\<span property\=\"name\" itemprop\=\"name\"\>[\s\t\r\n]+([^\<]+)[\s\t\r\n]+\<\/span\>'
            creatormatch = re.search(creatorregex, itempage.text)

            relatedcreatorregex = '\<div class\=\"detailField peopleField\"\>\<span class\=\"detailFieldLabel\"\>([^\<\/]+)\<\/span\>\<span class\=\"detailFieldValue\"\>\<a property\=\"url\" itemprop\=\"url\" href\=\"\/people\/(\d+)\/[^\"]+\"\>\<span property\=\"name\" itemprop\=\"name\"\>[\s\t\r\n]+([^\<]+)[\s\t\r\n]+\<\/span\>'
            relatedcreatormatch = re.search(relatedcreatorregex, itempage.text)

            # Some paintings have two lines: Unidentified and after ....
            # See for example https://emuseum.nyhistory.org/objects/41565/john-burgoyne-172231792
            # We want the after part
            if creatormatch:
                creatorname = htmlparser.unescape(creatormatch.group(2)).strip()

                if creatorname.lower()=='unidentified artist':
                    metadata['creatorname'] = creatorname.lower()
                    if relatedcreatormatch:
                        creatorprefix = htmlparser.unescape(relatedcreatormatch.group(1)).strip()
                        if creatorprefix != 'Depicted':
                            creatorname = '%s %s' % (htmlparser.unescape(relatedcreatormatch.group(1)).strip(),
                                                     htmlparser.unescape(relatedcreatormatch.group(3)).strip())
                            metadata['creatorname'] = creatorname
                    metadata['description'] = { 'en' : '%s %s' % ('painting', metadata.get('creatorname'),), }
                else:
                    metadata['creatorname'] = creatorname
                    metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }
            elif relatedcreatormatch:
                creatorname = '%s %s' % (htmlparser.unescape(relatedcreatormatch.group(1)).strip(),
                                         htmlparser.unescape(relatedcreatormatch.group(3)).strip())
                metadata['creatorname'] = creatorname
                metadata['description'] = { 'en' : '%s %s' % ('painting', metadata.get('creatorname'),),
                                            }

            dateregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class=\"detailFieldValue\"\>(\d\d\d\d)\<\/span\>'
            datecircaregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class=\"detailFieldValue\"\>[Cc]a?\.\s*(\d\d\d\d)\<\/span\>'
            periodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class=\"detailFieldValue\"\>(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)\<\/span\>'
            circaperiodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class=\"detailFieldValue\"\>[Cc]a?\.\s*(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)\<\/span\>'
            shortperiodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class=\"detailFieldValue\"\>(\d\d)(\d\d)[–-](\d\d)\<\/span\>'
            circashortperiodregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class=\"detailFieldValue\"\>[Cc]a?\. (\d\d)(\d\d)-(\d\d)\<\/span\>'
            otherdateregex = '\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class=\"detailFieldValue\"\>([^\<]+)\<\/span\>'

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
                if not otherdatematch.group(1)=='n.d' and not otherdatematch.group(1)=='n.d.' :
                    print ('Could not parse date: "%s"' % (otherdatematch.group(1),))

            ### Nothing useful here
            #acquisitiondateregex = '\<div class\=\"detailField creditlineField\"\>[^\<]+,\s*(\d\d\d\d)\<\/div\>'
            #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            #if acquisitiondatematch:
            #    metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = '\<span property\=\"artMedium\" itemprop\=\"artMedium\" class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>'
            mediummatch = re.search(mediumregex, itempage.text)
            # Artdatabot will sort this out
            if mediummatch:
                metadata['medium'] = mediummatch.group(1)

            # Dimensions seem to be including the frame so skipping it.
            #measurementsregex = '\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Dimensions\:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>([^\<]+cm)'
            #measurementsmatch = re.search(measurementsregex, itempage.text)
            #if measurementsmatch:
            #    measurementstext = measurementsmatch.group(1)
            #    regex_2d = '^(Unframed\s*)?H\s*(?P<height>\d+(\.\d+)?)\s*[×x]\s*W\s*(?P<width>\d+(\.\d+)?)\s*cm$'
            #    match_2d = re.match(regex_2d, measurementstext)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group('height').replace(',', '.')
            #        metadata['widthcm'] = match_2d.group('width').replace(',', '.')

            # Image url is provided and it's a US collection. Just check the date
            imageregex = '\<meta content\=\"(https\:\/\/emuseum\.nyhistory\.org\/internal\/media\/dispatcher\/\d+\/full)" property\=\"og\:image\"\>'
            imagematch = re.search(imageregex, itempage.text)
            # Disabled for now. A lot of undated images. Maybe later?
            #if imagematch:
            #    recentinception = False
            #    if metadata.get('inception') and metadata.get('inception') > 1924:
            #        recentinception = True
            #    if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
            #        recentinception = True
            #    if not recentinception:
            #        metadata['imageurl'] = imagematch.group(1)
            #        metadata['imageurlformat'] = 'Q2195' #JPEG
            #    #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
            #        metadata['imageoperatedby'] = 'Q2420849'
            #    #    # Used this to add suggestions everywhere
            #    #    metadata['imageurlforce'] = True
            yield metadata


def main(*args):
    dictGen = getNYhistoryGenerator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
