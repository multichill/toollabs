#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Städel Museum to Wikidata.

Just loop over pages like https://sammlung.staedelmuseum.de/en/search/2?q=term(48:object)&scope=all

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser
#import json

def getStadelGenerator():
    """
    Generator to return Städel Museum paintings
    """

    stadelArtists = getStadelArtistsOnWikidata()
    basesearchurl = u'https://sammlung.staedelmuseum.de/en/search/%s?q=term(48:object)&scope=all'
    htmlparser = HTMLParser()

    for i in range(1, 14):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workurlregex = u'\<a class\=\"dsSearchResultItem__link\" href\=\"\/en\/work\/([^\"]+)\"\>'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            # Just drop the slug
            url = u'https://sammlung.staedelmuseum.de/en/work/%s' % (match.group(1),)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)

            metadata['url'] = url

            deurlregex = u'\<link rel\=\"alternate\" hreflang\=\"de\" href\=\"\/\/sammlung\.staedelmuseum\.de\/de\/werk\/([^\"]+)\" \/\>'
            deurlmatch = re.search(deurlregex, itempage.text)

            deurl = u'https://sammlung.staedelmuseum.de/de/werk/%s' % (deurlmatch.group(1),)
            deitempage = requests.get(deurl)
            pywikibot.output(deurl)

            metadata['collectionqid'] = u'Q163804'
            metadata['collectionshort'] = u'Städel'
            metadata['locationqid'] = u'Q163804'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            #metadata['artworkidpid'] = u'P9999'
            #metadata['artworkid'] = workid

            metadata['idpid'] = u'P217'

            invregex = u'\<dt class\=\"dsProperty__caption\"\>Inventory Number\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*([^\<]+)\<\/dd\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            #titleregex = u'\<meta content\=\"([^\"]+)\" name\=\"og\:title\"\>'
            titleregex = u'\<meta property\=\"og:title\" content\=\"([^\"]+)\" \/\>'
            entitlematch = re.search(titleregex, itempage.text)
            detitlematch = re.search(titleregex, deitempage.text)

            entitle = htmlparser.unescape(entitlematch.group(1)).strip()
            detitle = htmlparser.unescape(detitlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(entitle) > 220:
                entitle = entitle[0:200]
            if len(detitle) > 220:
                detitle = detitle[0:200]
            metadata['title'] = { u'en' : entitle,
                                  u'de' : detitle,
                                  }

            creatoregex = u'\<p class\=\"dsArtwork__titleCreators\"\>[\r\n\t\s]*\<a class\=\"dsArtwork__titleCreator\" href\=\"\/(?P<lang>en|de)\/person\/(?P<id>[^\"]+)\" ontouchstart\=\"\"\>\<span class\=\"dsArtwork__titleCreatorName\"\>(?P<name>[^\<]+)\<\/span\>'
            derolecreatoregex = u'\<p class\=\"dsArtwork__titleCreators\"\>[\r\n\t\s]*\<a class\=\"dsArtwork__titleCreator\" href\=\"\/(?P<lang>en|de)\/person\/(?P<id>[^\"]+)\" ontouchstart\=\"\"\>\<span class\=\"dsArtwork__titleCreatorText\"\>(?P<role>[^\<]+)\<\/span\>\<span class\=\"dsArtwork__titleCreatorName\">(?P<name>[^\<]+)\<\/span\>'
            deroleregex = u'\<span class\=\"dsArtwork__titleCreatorText\"\>\s*(?P<role>[^\<]+)\<\/span\>'

            encratormatch = re.search(creatoregex, itempage.text)
            decratormatch = re.search(creatoregex, deitempage.text)

            #enrolecratormatch = re.search(creatoregex, itempage.text)
            derolecratormatch = re.search(derolecreatoregex, deitempage.text)
            derolematch = re.search(deroleregex, deitempage.text)

            # We found a copy or something in that direction
            if derolecratormatch or derolematch:
                if derolecratormatch:
                    name = derolecratormatch.group(u'name')
                    role = derolecratormatch.group(u'role')
                else:
                    name = decratormatch.group(u'name')
                    role = derolematch.group(u'role')
                metadata['description'] = { u'de' : u'%s %s %s' % (u'Gemälde', role.lower(), name),
                                            }
                #Want to run without this first
                #metadata['creatorqid'] = u'Q4233718'
            else:
                enartistid = encratormatch.group(2)
                deartistid = decratormatch.group(2)
                enname = htmlparser.unescape(encratormatch.group(3)).strip()
                dename = htmlparser.unescape(decratormatch.group(3)).strip()

                metadata['creatorname'] = enname

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            u'de' : u'%s von %s' % (u'Gemälde', dename, ),
                                            u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                            }

                if enartistid in stadelArtists:
                    pywikibot.output (u'Found Städel Museum artist ID in English %s on %s' % (enartistid, stadelArtists.get(enartistid)))
                    metadata['creatorqid'] = stadelArtists.get(enartistid)
                elif deartistid in stadelArtists:
                    pywikibot.output (u'Found Städel Museum artist ID in German %s on %s' % (deartistid, stadelArtists.get(deartistid)))
                    metadata['creatorqid'] = stadelArtists.get(deartistid)
                else:
                    pywikibot.output (u'Artist id %s & %s on %s & %s not found on Wikidata' % (enartistid, deartistid, url, deurl))
                    pywikibot.output (u'Artist id %s & %s on %s & %s not found on Wikidata' % (enartistid, deartistid, url, deurl))
                    pywikibot.output (u'Artist id %s & %s on %s & %s not found on Wikidata' % (enartistid, deartistid, url, deurl))
                    pywikibot.output (u'Artist id %s & %s on %s & %s not found on Wikidata' % (enartistid, deartistid, url, deurl))

            """
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
            """
            yield metadata


def getStadelArtistsOnWikidata():
    """
    Just return all the Städel Museum people as a dict
    :return: Dict
    """
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P4581 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result


def main():
    dictGen = getStadelGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
