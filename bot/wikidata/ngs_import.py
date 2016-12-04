#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the National Galleries of Scotland to Wikidata.

Just loop over pages like https://art.nationalgalleries.org/search?object_types[29864]=29864&page=0
Start at http://www.bellasartes.gob.ar/coleccion/objeto/pintura and use a session to retrieve the rest.

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getNGSGenerator():
    """
    Generator to return National Galleries of Scotland paintings
    """
    basesearchurl = u'https://art.nationalgalleries.org/search?object_types[29864]=29864&page=%s'
    htmlparser = HTMLParser.HTMLParser()

    for i in range (0,125):
        urls = []
        searchurl = basesearchurl % (i,)
        print searchurl
        searchPage = requests.get(searchurl)
        urlregex = u'\<a href\=\"(\/art-and-artists\/\d+\/[^\?]+)\?object_types\[29864\]=2986[^\"]+\"' # ?
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            # To remove duplicates
            url = u'https://art.nationalgalleries.org%s' % (match.group(1))
            if url not in urls:
                urls.append(url)

        for url in urls:
            metadata = {}

            print url

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q2051997'
            metadata['collectionshort'] = u'NGoS'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            invregex = u'\<li class\=\"ngs-mimsy-data__item\"\>\s*\<span class\=\"ngs-mimsy-data__item-label\"\>accession number\:</span\>\s*\<span class\=\"ngs-mimsy-data__item-values\"\>([^\<]+)\<\/span\>\<\/li\>'
            invmatch = re.search(invregex, itempage.text)

            if not invmatch:
                pywikibot.output(u'Something went wrong, skipping this one')
                continue

            metadata['id'] = invmatch.group(1).strip()
            metadata['idpid'] = u'P217'

            # They have three locations, using inventory to guess the location
            if metadata['id'].startswith(u'NG ') or metadata['id'].startswith(u'NGL '):
                metadata['locationqid'] = u'Q942713' # Scottish National Gallery (Q942713)
            elif metadata['id'].startswith(u'PG '):
                metadata['locationqid'] = u'Q2441562' # Scottish National Portrait Gallery (Q2441562)
            elif metadata['id'].startswith(u'GMA '):
                metadata['locationqid'] = u'Q1889944' # Scottish National Gallery of Modern Art (Q1889944)
            else:
                metadata['locationqid'] = u'Q2051997'

            titleregex = u'\<li class\=\"ngs-mimsy-data__item\"\>\s*\<span class\=\"ngs-mimsy-data__item-label\"\>title\:</span\>\s*\<span class\=\"ngs-mimsy-data__item-values\"\>([^\<]+)\<\/span\>\<\/li\>'
            titlematch = re.search(titleregex, itempage.text)
            #if not titlematch:
            #    pywikibot.output(u'No title match, something went wrong on %s' % (url,))
            #    continue
            ## Chop chop, several very long titles
            #if title > 220:
            #    title = title[0:200]
            metadata['title'] = { u'en' : htmlparser.unescape(titlematch.group(1).strip()),
                                  }

            creatorregex = u'\<li class\=\"ngs-mimsy-data__item\"\>\s*\<span class\=\"ngs-mimsy-data__item-label\"\>artists?\:</span\>\s*\<span class\=\"ngs-mimsy-data__item-values\"\>(\<a href\=\"[^\"]+\" title=\"[^\"]+\"\>)?(?P<creator>[^\<]+)\<\/'
            creatormatch = re.search(creatorregex, itempage.text)
            name = htmlparser.unescape(creatormatch.group(u'creator').strip())
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            if name==u'Unknown':
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            else:
                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', name,),
                                            u'en' : u'%s by %s' % (u'painting', name,),
                                            }

            acquisitiondateregex = u'\<li class\=\"ngs-mimsy-data__item\"\>\s*\<span class\=\"ngs-mimsy-data__item-label\"\>credit line\:</span\>\s*\<span class\=\"ngs-mimsy-data__item-values\"\>[^\<]+(\d\d\d\d)\<\/span\>\<\/li\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            inceptionregex = u'\<li class\=\"ngs-mimsy-data__item\"\>\s*\<span class\=\"ngs-mimsy-data__item-label\"\>date created\:</span\>\s*\<span class\=\"ngs-mimsy-data__item-values\"\>(\d\d\d\d)\<\/span\>\<\/li\>'
            inceptionmatch = re.search(inceptionregex, itempage.text)
            if inceptionmatch:
                metadata['inception'] = inceptionmatch.group(1)

            mediumregex = u'\<li class\=\"ngs-mimsy-data__item\"\>\s*\<span class\=\"ngs-mimsy-data__item-label\"\>medium\:</span\>\s*\<span class\=\"ngs-mimsy-data__item-values\"\>([^\<]+)\<\/span\>\<\/li\>'

            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch and mediummatch.group(1) == u'Oil on canvas':
                metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<li class\=\"ngs-mimsy-data__item\"\>\s*\<span class\=\"ngs-mimsy-data__item-label\"\>measurements\:</span\>\s*\<span class\=\"ngs-mimsy-data__item-values\"\>([^\<]+)\<\/span\>\<\/li\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm.*'
                regex_3d = u'(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            yield metadata


def main():
    dictGen = getNGSGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
