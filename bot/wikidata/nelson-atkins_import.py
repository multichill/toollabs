#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Nelson-Atkins Museum of Art to Wikidata.

Just loop over pages like https://art.nelson-atkins.org/objects/images?filter=thesfilter%3A1545168&page=2

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser
#import json

def getNAGenerator():
    """
    Generator to return Nelson-Atkins Museum of Art paintings
    """

    naArtists = getNAArtistsOnWikidata()
    basesearchurl = u'https://art.nelson-atkins.org/objects/images?filter=thesfilter%%3A1545168&page=%s'
    htmlparser = HTMLParser()

    for i in range(1, 150):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workidregex = u'href\=\"/objects/(\d+)/'
        matches = re.finditer(workidregex, searchPage.text)
        idlist = []

        for match in matches:
            if match.group(1) not in idlist:
                idlist.append(match.group(1))


        for workid in idlist:
            # Just drop the slug
            url = u'https://art.nelson-atkins.org/objects/%s/' % (workid,)
            metadata = {}

            itempage = requests.get(url)


            metadata['url'] = url

            metadata['collectionqid'] = u'Q1976985'
            metadata['collectionshort'] = u'Nelson-Atkins'
            metadata['locationqid'] = u'Q1976985'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            #metadata['artworkidpid'] = u'P9999'
            #metadata['artworkid'] = workid

            metadata['idpid'] = u'P217'

            invregex = u'\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldLabel\"\>Object number: \<\/span\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            titleregex = u'\<meta content\=\"([^\"]+)\" name\=\"og\:title\"\>'
            titlematch = re.search(titleregex, itempage.text)

            title = htmlparser.unescape(titlematch.group(1)).strip()

            ## Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }

            # Creator is a bit messy
            artistwithidregex = u'\<span class\=\"detailFieldLabel\"\>Artist: \<\/span\>\<span class\=\"detailFieldValue\"\>\<a href\=\"\/people\/(\d+)\/[^\"]+\"\>\<span\>([^\<]+)\<\/span\>'
            attributedwithidregex = u'\<span class\=\"detailFieldLabel\"\>Attributed to: \<\/span\>\<span class\=\"detailFieldValue\"\>\<a href\=\"\/people\/(\d+)\/[^\"]+\"\>\<span\>Attributed to \<\/span\>\<span\>([^\<]+)\<\/span\>'
            schemacreatorregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema:creator\" itemprop\=\"creator\"\>'
            cultureregex = u'\<div class\=\"detailField cultureField\"\>\<span class\=\"detailFieldLabel\"\>Culture: \<\/span\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>'


            artistwithidmatch = re.search(artistwithidregex, itempage.text)
            attributedwithidmatch = re.search(attributedwithidregex, itempage.text)
            schemacreatormatch = re.search(schemacreatorregex, itempage.text)
            culturematch = re.search(cultureregex, itempage.text)
            culture = None
            if culturematch:
                culture = htmlparser.unescape(culturematch.group(1)).strip()
                print (u'CULTURE MATCH: %s' % (culture,))
                print (u'CULTURE MATCH: %s' % (culture,))
                print (u'CULTURE MATCH: %s' % (culture,))
                print (u'CULTURE MATCH: %s' % (culture,))

            if artistwithidmatch and schemacreatormatch and artistwithidmatch.group(2)==schemacreatormatch.group(1):
                print (u'Artist everything adds up: %s' % (artistwithidmatch.group(2),))
                print (u'Artist everything adds up: %s' % (artistwithidmatch.group(2),))
                print (u'Artist everything adds up: %s' % (artistwithidmatch.group(2),))
                print (u'Artist everything adds up: %s' % (artistwithidmatch.group(2),))

                if artistwithidmatch.group(2)==u'Unknown' and culture:
                    metadata['description'] = { u'en' : u'painting by anonymous %s painter' % (culture, ),
                                                }
                    metadata['creatorqid'] = u'Q4233718'
                elif artistwithidmatch.group(2)==u'Unknown':
                    metadata['description'] = { u'en' : u'painting by anonymous painter',
                                                }
                    metadata['creatorqid'] = u'Q4233718'
                else:
                    name = htmlparser.unescape(artistwithidmatch.group(2)).strip()
                    metadata['creatorname'] = name
                    metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                                u'en' : u'painting by %s' % (name, ),
                                                u'de' : u'Gemälde von %s' % (name, ),
                                                }
                    artistid = artistwithidmatch.group(1)
                    print (artistid)
                    if artistid in naArtists:
                        pywikibot.output (u'Found Nelson-Atkins Museum of Art person ID %s on %s' % (artistid, naArtists.get(artistid)))
                        metadata['creatorqid'] = naArtists.get(artistid)
            elif attributedwithidmatch and schemacreatormatch and attributedwithidmatch.group(2)==schemacreatormatch.group(1):
                print (u'Artist attributed adds up: %s' % (attributedwithidmatch.group(2),))
                print (u'Artist attributed adds up: %s' % (attributedwithidmatch.group(2),))
                print (u'Artist attributed adds up: %s' % (attributedwithidmatch.group(2),))
                print (u'Artist attributed adds up: %s' % (attributedwithidmatch.group(2),))

                # Artdatabot doesn't support adding attribution yet
                name = htmlparser.unescape(attributedwithidmatch.group(2)).strip()
                metadata['creatorname'] = name
                metadata['description'] = { u'en' : u'painting attributed to %s' % (name, ),
                                            }

            elif culture:
                metadata['description'] = { u'en' : u'painting by anonymous %s painter' % (culture, ),
                                            }
                metadata['creatorqid'] = u'Q4233718'

            elif artistwithidmatch or schemacreatormatch:
                if artistwithidmatch:
                    print (u'Did get an artist with id match: %s' % (artistwithidmatch.group(2),))
                    print (u'Did get an artist with id match: %s' % (artistwithidmatch.group(2),))
                    print (u'Did get an artist with id match: %s' % (artistwithidmatch.group(2),))
                if schemacreatormatch:
                    print (u'Did get an schema creator match: %s' % (schemacreatormatch.group(1),))
                    print (u'Did get an schema creator match: %s' % (schemacreatormatch.group(1),))
                    print (u'Did get an schema creator match: %s' % (schemacreatormatch.group(1),))
            else:
                print (u'Didn\'t find creator info')

            # Older paintings have more difficult dates
            dateregex = u'\<meta content\=\"(\d\d\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            datecircaregex = u'\<meta content\=\"ca\. (\d\d\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            periodregex = u'\<meta content\=\"(\d\d\d\d)-?\/?(\d\d\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            circaperiodregex = u'\<meta content\=\"ca\. (\d\d\d\d)-(\d\d\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            shortperiodregex = u'\<meta content\=\"(\d\d)(\d\d)–(\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            #circashortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d)(\d\d)–(\d\d)\<\/p\>'
            otherdateregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'

            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            periodmatch = re.search(periodregex, itempage.text)
            circaperiodmatch = re.search(circaperiodregex, itempage.text)
            shortperiodmatch = re.search(shortperiodregex, itempage.text)
            circashortperiodmatch = None
            otherdatematch = re.search(otherdateregex, itempage.text)

            if datematch:
                metadata['inception'] = datematch.group(1).strip()
            elif datecircamatch:
                metadata['inception'] = datecircamatch.group(1).strip()
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
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # A bit of provenance data
            acquisitiondateregex = u'(by|to) The Nelson-Atkins Museum of Art, Kansas City, MO, (\d\d\d\d)\.'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(2)

            mediumregex = u'\<meta content\=\"Oil on canvas\" property\=\"schema:artMedium\" itemprop\=\"artMedium\"\>'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            # Bit messy, this will get some of them
            measurementsregex = u'\<span class\=\"detailFieldLabel\"\>Dimensions:\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>(Unframed|Overall):[^\<]+(inches|in\.)\s*\(([^\<]+cm)\)\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(3)
                print (measurementstext)
                print (measurementstext)
                print (measurementstext)
                print (measurementstext)
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

            # They have IIIF!
            # <a class="iiifLink" href="https://art.nelson-atkins.org/apis/iiif/presentation/v2/objects-7769/manifest">
            # They insert a stupid Emuseum session id?
            iiifregex = u'\<a class\=\"iiifLink\" href\=\"https\:\/\/art\.nelson-atkins\.org\/apis\/iiif\/presentation\/v2\/objects-(\d+)'
            iiifmatch = re.search(iiifregex, itempage.text)
            if iiifmatch:
                metadata['iiifmanifesturl'] = u'https://art.nelson-atkins.org/apis/iiif/presentation/v2/objects-%s/manifest' % (iiifmatch.group(1),)

            yield metadata


def getNAArtistsOnWikidata():
    '''
    Just return all the Whitney people as a dict
    :return: Dict
    '''
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P5273 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result


def main():
    dictGen = getNAGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
