#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  National Gallery of Canada (Musée des Beaux-Arts du Canada) to Wikidata.

Just loop over pages like https://www.gallery.ca/collection/search-the-collection?f[0]=field_object_medium%3A4753&page=0

"""
import artdatabot
import pywikibot
import requests
import re
import time
try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getGalleryCaGenerator():
    """
    Generator to return National Gallery of Canada paintings
    """
    basesearchurl = u'https://www.gallery.ca/collection/search-the-collection?f[0]=field_object_medium%%3A4753&page=%s'

    htmlparser = HTMLParser()

    galleryCaArtists = getGalleryCaArtistsOnWikidata()

    # Make the lookup table here!

    for i in range(0, 845): # 4223 works with 5 per page
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        urlregex = u'\<div\s*about\=\"(https\:\/\/www\.gallery\.ca\/collection\/artwork\/[^\"]+)\" typeof\=\"sioc:Item foaf:Document\"'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = match.group(1)
            print (url)

            # No artwork pid here
            #metadata['artworkidpid'] = u'P5823'
            #metadata['artworkid'] = match.group(2)
            itempage = requests.get(url)

            metadata['url'] = url
            metadata['collectionqid'] = u'Q1068063'
            metadata['collectionshort'] = u'NGA Canada'
            metadata['locationqid'] = u'Q1068063'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            invregex = u'\<div class\=\"artwork-field\"\>\<div class\=\"label-above\"\>Accession number\<\/div\>\<div\>([^\<]+)\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            titleregex = u'\<meta property\=\"og:title\" content\=\"([^\"]+)\" \/\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1).strip())
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]

            frtitleregex = u'\<a href\=\"https\:\/\/www\.beaux-arts\.ca\/collection\/artwork\/[^\"]+\" class\=\"language-link\" xml:lang\=\"fr\" title\=\"([^\"]+)\"\>FR\<\/a\>'
            frtitlematch = re.search(frtitleregex, itempage.text)
            if frtitlematch:
                frtitle = htmlparser.unescape(frtitlematch.group(1).strip())
            else:
                # In rare cases the English title is used in French
                frtitle = title
            # Chop chop, several very long titles
            if len(frtitle) > 220:
                frtitle = frtitle[0:200]

            metadata['title'] = { u'en' : title,
                                  u'fr' : frtitle,
                                  }

            creatorregex = u'\<div\>\<a href\=\"https\:\/\/www\.gallery\.ca\/collection\/artist\/([^\"]+)\"\>([^\<]+)\<\/a\>'
            creatormatch = re.search(creatorregex, itempage.text)
            # Should alway be a match most of the time
            if creatormatch:
                artistid = creatormatch.group(1).strip()
                name = htmlparser.unescape(creatormatch.group(2).strip())
            else:
                artistid = u'unknown'
                name = u'unknown'

            # Do artist lookup here
            if artistid in galleryCaArtists:
                pywikibot.output (u'Found National Gallery of Canada artist ID %s on %s' % (artistid, galleryCaArtists.get(artistid)))
                metadata['creatorqid'] = galleryCaArtists.get(artistid)
            else:
                pywikibot.output (u'National Gallery of Canada artist ID %s not found on Wikidata' % (artistid,))

            if artistid==u'unknown':
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
            else:
                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                            u'en' : u'painting by %s' % (name, ),
                                            u'de' : u'Gemälde von %s' % (name, ),
                                            u'fr' : u'peinture de %s' % (name, ),
                                            }

            dateregex = u'\<div class\=\"artwork-field\"\>\<div class\=\"label-above\"\>Date\<\/div\>\<div\>(\d\d\d\d)\<\/div\>'
            datematch = re.search(dateregex, itempage.text)
            if datematch:
                metadata['inception'] = htmlparser.unescape(datematch.group(1).strip())
            else:
                datecircaregex = u'\<div class\=\"artwork-field\"\>\<div class\=\"label-above\"\>Date\<\/div\>\<div\>c\.\s*(\d\d\d\d)\<\/div\>'
                datecircamatch = re.search(datecircaregex, itempage.text)
                if datecircamatch:
                    metadata['inception'] = htmlparser.unescape(datecircamatch.group(1).strip())
                    metadata['inceptioncirca'] = True

            # Just get the last year in the field
            acquisitiondateregex = u'\<div class\=\"artwork-field\"\><div class\=\"label-above\"\>Credit line\<\/div\>\<div\>[^\<]+(\d\d\d\d)\<\/div\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            mediumregex = u'\<div class\=\"field artwork-field\"\>\<div class\=\"label-above field-label\"\>Materials\<\/div\>oil on canvas\<\/div\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<div class\=\"artwork-field\"\>\<div class\=\"label-above\"\>Dimensions\<\/div\>\<div\>([^\<]+)\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm'
                regex_3d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height')
                    metadata['widthcm'] = match_3d.group(u'width')
                    metadata['depthcm'] = match_3d.group(u'depth')

            # Image is available, but not free
            #imageurlregex = u'\<link rel\=\"image_src\" href\=\"([^\"]+jpg)\" \/\>'
            #imageurlmatch = re.search(imageurlregex, itempage.text)
            #if imageurlmatch:
            #    metadata[u'imageurl'] = imageurlmatch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            #    #metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa-4.0
            #    # Could use this later to force
            #    metadata[u'imageurlforce'] = False
            # No IIIF
            yield metadata

def getGalleryCaArtistsOnWikidata():
    '''
    Just return all the National Gallery of Canada people as a dict
    :return: Dict
    '''
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P5368 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result

def main():
    dictGen = getGalleryCaGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
