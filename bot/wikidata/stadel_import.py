#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Städel Museum to Wikidata. Currently broken, needs to be updated for the new website

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

    motifs = { 26 : 'Q134307', # portrait
               44 : 'Q191163', # landscape -> landscape art
               1955 : 'Q2864737', # altarpiece-> religious art
               2437 : 'Q170571', # still life
               2957 : 'Q1047337', # genre art
               3657 : 'Q2864737', # devotional image -> religious art
               3706 : 'Q40446', # nude
               3796 : 'Q158607', # Seascape -> marine art
               3901 : 'Q2839016', # allegory
               8730 : 'Q128115', # abstration -> abstract art
               14293 : 'Q2864737', # Biblical portrayal-> religious art
               16679 : 'Q3374376', # mythological representation -> mythological painting
               }

    stadelArtists = getStadelArtistsOnWikidata()
    basesearchurl = 'https://sammlung.staedelmuseum.de/en/search/%s?q=term(48:object)&scope=all'
    # basesearchurl = 'https://sammlung.staedelmuseum.de/en/search?f=+object:term(48)&flags=allScopes&p=%s'
    htmlparser = HTMLParser()

    for i in range(1, 15):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workurlregex = '\<a class\=\"dsSearchResultItem__link\" href\=\"\/en\/work\/([^\"]+)\"\>'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            # Just drop the slug
            url = 'https://sammlung.staedelmuseum.de/en/work/%s' % (match.group(1),)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)

            metadata['url'] = url

            deurlregex = '\<link rel\=\"alternate\" hreflang\=\"de\" href\=\"https:\/\/sammlung\.staedelmuseum\.de\/de\/werk\/([^\"]+)\" \/\>'
            deurlmatch = re.search(deurlregex, itempage.text)

            deurl = 'https://sammlung.staedelmuseum.de/de/werk/%s' % (deurlmatch.group(1),)
            deitempage = requests.get(deurl)
            pywikibot.output(deurl)

            metadata['collectionqid'] = 'Q163804'
            metadata['collectionshort'] = 'Städel'
            metadata['locationqid'] = 'Q163804'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            #metadata['artworkidpid'] = u'P9999'
            #metadata['artworkid'] = workid

            metadata['idpid'] = u'P217'

            invregex = '\<dt class\=\"dsProperty__caption\"\>Inventory Number\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*([^\<]+)\<\/dd\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace('&nbsp;', u' ')).strip()

            # When it's a work with multiple parts, they add "Object Number". Overwrite the inventory number based on that
            objectnumberregex = '\<dt class\=\"dsProperty__caption\"\>Object Number\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*([^\<]+)\<\/dd\>'
            objectnumbermatch = re.search(objectnumberregex, itempage.text)
            if objectnumbermatch:
                metadata['id'] = htmlparser.unescape(objectnumbermatch.group(1).replace('&nbsp;', ' ')).strip()

            #titleregex = u'\<meta content\=\"([^\"]+)\" name\=\"og\:title\"\>'
            titleregex = '\<meta property\=\"og:title\" content\=\"([^\"]+)\" \/\>'
            entitlematch = re.search(titleregex, itempage.text)
            detitlematch = re.search(titleregex, deitempage.text)

            entitle = htmlparser.unescape(entitlematch.group(1)).strip()
            detitle = htmlparser.unescape(detitlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(entitle) > 220:
                entitle = entitle[0:200]
            if len(detitle) > 220:
                detitle = detitle[0:200]
            metadata['title'] = { 'en' : entitle,
                                  'de' : detitle,
                                  }

            creatoregex = '\<p class\=\"dsArtwork__titleCreators\"\>[\r\n\t\s]*\<a class\=\"dsArtwork__titleCreator\" href\=\"\/(?P<lang>en|de)\/person\/(?P<id>[^\"]+)\" ontouchstart\=\"\"\>\<span class\=\"dsArtwork__titleCreatorName\"\>(?P<name>[^\<]+)\<\/span\>'
            derolecreatoregex = '\<p class\=\"dsArtwork__titleCreators\"\>[\r\n\t\s]*\<a class\=\"dsArtwork__titleCreator\" href\=\"\/(?P<lang>en|de)\/person\/(?P<id>[^\"]+)\" ontouchstart\=\"\"\>\<span class\=\"dsArtwork__titleCreatorText\"\>(?P<role>[^\<]+)\<\/span\>\<span class\=\"dsArtwork__titleCreatorName\">(?P<name>[^\<]+)\<\/span\>'
            deroleregex = '\<span class\=\"dsArtwork__titleCreatorText\"\>\s*(?P<role>[^\<]+)\<\/span\>'

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

            # Let's see if we can extract some dates. Json-ld is provided, but doesn't have circa and the likes
            dateregex = u'\<span class\=\"dsArtwork__titleYear\"\>,\s*(\d\d\d\d)\<\/span\>'
            datecircaregex = u'\<span class\=\"dsArtwork__titleYear\"\>,\s*ca\.\s*(\d\d\d\d)\<\/span\>'
            periodregex = u'\<span class\=\"dsArtwork__titleYear\"\>,\s*(\d\d\d\d)\s*&ndash;\s*(\d\d\d\d)\<\/span\>'
            circaperiodregex = u'\<span class\=\"dsArtwork__titleYear\"\>,\s*ca\.\s*(\d\d\d\d)\s*&ndash;\s*(\d\d\d\d)\<\/span\>'
            #shortperiodregex = u'\<meta content\=\"(\d\d)(\d\d)–(\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            #circashortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d)(\d\d)–(\d\d)\<\/p\>'
            otherdateregex = u'\<span class\=\"dsArtwork__titleYear\"\>([^\<]+)\<\/span\>'

            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            periodmatch = re.search(periodregex, itempage.text)
            circaperiodmatch = re.search(circaperiodregex, itempage.text)
            shortperiodmatch = None
            circashortperiodmatch = None
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
                metadata['inceptionstart'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
            elif circashortperiodmatch:
                metadata['inceptionstart'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                metadata['inceptionend'] = int('%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # A bit of provenance data
            acquisitiondateregex = u'\<dt class\=\"dsProperty__caption\"\>Acquisition\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*Acquired in (\d\d\d\d)'
            loandateregex = u'\<dt class\=\"dsProperty__caption\"\>Acquisition\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*On permanent loan from\s*([^\<]+)\s*since\s*(\d\d\d\d)\<\/dd\>'
            missedacquisitionregex = u'\<dt class\=\"dsProperty__caption\"\>Acquisition\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*([^\<]+)\<\/dd\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            loandatematch = re.search(loandateregex, itempage.text)
            missedacquisitiondatematch = re.search(missedacquisitionregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)
            elif loandatematch:
                metadata['acquisitiondate'] = loandatematch.group(2)
            elif missedacquisitiondatematch:
                print (u'Could not parse date: "%s"' % (missedacquisitiondatematch.group(1),))

            mediumregex = u'\<dt class\=\"dsProperty__caption\">Physical Description\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*([^\<]+)\s*\<'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                medium = mediummatch.group(1)
                mediums = { 'Oil on canvas' : 'oil on canvas',
                            'Oil on oak' : 'Oil on oak panel',
                            }
                if medium in mediums:
                    metadata['medium'] = mediums.get(medium)
                else:
                    print('I hope that artdadabot understands medium %s' % (medium,))
                    metadata['medium'] = medium.lower()

            # Look for genre
            motifregex = u'\<a class\=\"dsTerm\" href\=\"\/en\/search\?scope\=all&amp;q\=term\((\d+)\:motif_general\)\" ontouchstart\=\"\"\>([^\<]+)\<\/a\>'
            motifmatch = re.search(motifregex, itempage.text)
            if motifmatch:
                motifid = int(motifmatch.group(1))
                print (u'Motif match with id %s and description %s' % (motifid, motifmatch.group(2)))
                if motifid in motifs:
                    metadata[u'genreqid'] = motifs.get(motifid)

            # Movement is also available

            measurementsregex = u'\<dt class\=\"dsProperty__caption\"\>Dimensions\<\/dt\>\<dd class\=\"dsProperty__text\"\>([^\<]+)\<\/dd\>'
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

            ## Download is interesting
            #downloadregex = '\<button class\=\"dsArtworkActions__button\" data-action\=\"download\" data-target\=\"(\/en\/work\/[^\"]+\/download)\"\>'
            #downloadmatch = re.search(downloadregex, itempage.text)
            #if downloadmatch:
            #    downloadurl = 'https://sammlung.staedelmuseum.de%s' % (downloadmatch.group(1),)
            #    postdata = {'command': 'download', 'sources[]' : '__default__'}
            #    downloadpage = requests.post(downloadurl, data=postdata)
            #    print (downloadpage.json())
            # This does contain the download url in the json, but the website will throw an error at you

            iconclass_regex = '<a class="dsTerm" href="/en/search\?scope=all&amp;q=term\(\d+:iconclass\)">([^<]+)</a>'
            iconclass_matches = re.finditer(iconclass_regex, itempage.text)
            if iconclass_matches:
                metadata['depictsiconclass'] = []
                for iconclass_match in iconclass_matches:
                    metadata['depictsiconclass'].append(htmlparser.unescape(iconclass_match.group(1)).strip())
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


def main(*args):
    dictGen = getStadelGenerator()
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
