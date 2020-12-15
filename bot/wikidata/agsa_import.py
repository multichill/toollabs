#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Art Gallery of South Australia to Wikidata.

Just loop over pages like https://www.agsa.sa.gov.au/collection-publications/collection/?medium=Painting&type=work&work-sort=relevance&has-images=no&on-display=no&page=2

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getAGSAGenerator():
    """
    Generator to return AGSA paintings
    """
    basesearchurl = 'https://www.agsa.sa.gov.au/collection-publications/collection/?medium=Painting&type=work&work-sort=relevance&has-images=no&on-display=no&page=%s'
    htmlparser = HTMLParser()

    session = requests.Session()
    artists = agsaArtistsOnWikidata()

    # 2195 hits, 24 per page.
    for i in range(1, 93):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = session.get(searchurl)

        workurlregex = '\<a class\=\"collection-work-item__thumb-link\" href\=\"\/collection-publications\/collection\/works\/([^\"]+)\/(\d+)\/\">'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            metadata = {}
            slug = match.group(1)
            agsaid = '%s' % (match.group(2),)
            url = 'https://www.agsa.sa.gov.au/collection-publications/collection/works/%s/%s' % (slug, agsaid,)

            itempage = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q705557'
            metadata['collectionshort'] = 'AGSA'
            metadata['locationqid'] = 'Q705557'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            # Get the  Art Gallery of South Australia work ID (P6805)
            metadata['artworkid'] = agsaid
            metadata['artworkidpid'] = 'P6805'

            # Can get everything from a bunch of meta properties. Something like beautifulsoup might be better here.

            invregex = '\<meta itemprop\=\"identifier\" content\=\"Accession number\:\s*([^\"]+)\"\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace('&nbsp;', ' ')).strip()

            titleregex = '\<meta property\=\"og\:title\" content\=\"([^\"]+)\"\/\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'en' : title,
                                  }

            creatorregex = '\<meta itemprop\=\"creator\" content\=\"([^\"]+)\"\>'
            creatormatch = re.search(creatorregex, itempage.text)
            if creatormatch:
                creatorname = htmlparser.unescape(creatormatch.group(1)).strip()

                metadata['creatorname'] = creatorname
                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }
            else:
                print('NO CREATOR FOUND!!!!')

            creatoridregex = 'class\=\"collection-detail-work-details__creator-link\"[\r\n\s\t]+href\=\"\/collection-publications\/collection\/creators\/[^\"]+\/(\d+)\/\"'
            creatoridmatch = re.search(creatoridregex, itempage.text)
            if creatoridmatch:
                creatorid = creatoridmatch.group(1)
                if creatorid in artists:
                    pywikibot.output ('Found AGSA artists id %s on %s' % (creatorid, artists.get(creatorid)))
                    metadata['creatorqid'] = artists.get(creatorid)

            # Quick and dirty, seems to catch most of it.
            dateregex = '\<meta itemprop\=\"dateCreated\" content\=\"(\d\d\d\d)\"\>'
            datecircaregex = '\<meta itemprop\=\"dateCreated\" content\=\"ca?\.\s*(\d\d\d\d)\"\>'
            periodregex = '\<meta itemprop\=\"dateCreated\" content\=\"(\d\d\d\d)\s*-\s*(\d\d\d\d)\"\>'
            circaperiodregex = '\<meta itemprop\=\"dateCreated\" content\=\"ca?\.\s*(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)\"\>'
            shortperiodregex = '\<meta itemprop\=\"dateCreated\" content\=\"(\d\d)(\d\d)\s*[–-]\s*(\d\d)\"\>'
            circashortperiodregex = '\<meta itemprop\=\"dateCreated\" content\=\"ca?\.\s*(\d\d)(\d\d)\s*[–-]\s*(\d\d)\"\>'
            otherdateregex = '\<meta itemprop\=\"dateCreated\" content\=\"([^\"]+)\"\>'

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
            acquisitiondateregex = '\<meta itemprop\=\"sponsor\" content\=\"[^\"]*(\d\d\d\d)\"\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = '\<meta itemprop\=\"material\" content\=\"oil on canvas\"\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = 'oil on canvas'

            # Dimensions are in the text
            measurementsregex = '\<dt\>Dimensions\<\/dt\>[\r\n\s\t]+\<dd\>[\r\n\s\t]+([^c]+cm)'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = '^(?P<height>\d+(\.\d+)?)\s*[×x]\s*(?P<width>\d+(\.\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group('width').replace(',', '.')

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

def agsaArtistsOnWikidata():
    """
    Just return all the AGSA people as a dict
    :return: Dict
    """
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:P6804 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
        result[resultitem.get('id')] = qid
    return result

def main(*args):
    dictGen = getAGSAGenerator()
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
