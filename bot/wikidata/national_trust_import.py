#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from the National Trust (Collections) to Wikidata

* Loop over http://www.nationaltrustcollections.org.uk/results?Categories=7456ee20fffffe0702132e04e5764fd3&Sort=collection
* Grab individual paintings like http://www.nationaltrustcollections.org.uk/object/1514019
* Also do some tricks to match the location

Use artdatabot to upload it to Wikidata

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

def getNTGenerator():
    """
    Generator to return National Trust paintings

    Search has a max of 250 pages, so that's 5*5*250=6250 of the 12,472 paintings.
    So need to try the different ways to get all of them.
    
    """
    htmlparser = HTMLParser()
    locations = nationalTrustLocationsOnWikidata()
    missedlocations = {} # Where it is now
    missedplaces = {} # Where it was made
    baseSearchUrl = u'http://www.nationaltrustcollections.org.uk/results?Categories=7456ee20fffffe0702132e04e5764fd3&Sort=collection&Page=%s'

    for i in range(1, 250):
        print (missedlocations)
        searchUrl = baseSearchUrl % (i,)
        print (searchUrl)

        searchPage = requests.get(searchUrl)
        searchPageData = searchPage.text
        searchRegex = u'\<a href\=\"\/object\/([\d+\.]+)\"\>'

        for match in re.finditer(searchRegex, searchPageData):
            url = u'http://www.nationaltrustcollections.org.uk/object/%s' % (match.group(1),)

            print (url)

            itemPage = requests.get(url)
            itemPageData = itemPage.text

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = u'Q333515'
            metadata['collectionshort'] = u'NT'

            locationregex = u'\<h4\>Collection\<\/h4\>[\r\n\t\s]*\<p\>([^\<]+)\<\/p\>[\r\n\t\s]*\<h4\>On show at\<\/h4\>[\r\n\t\s]*\<p\>\<a href\=\"https?\:\/\/www\.nationaltrust\.org\.uk\/([^\"]+)\"'
            locationMatch = re.search(locationregex, itemPageData)

            location2regex = u'\<h4\>Collection\<\/h4\>[\r\n\t\s]*\<p\>([^\<]+)\<\/p\>[\r\n\t\s]*\<h4\>On show at\<\/h4\>'
            location2Match = re.search(location2regex, itemPageData)

            if locationMatch:
                #print (locationMatch.group(1))
                #print (locationMatch.group(2))
                location = locationMatch.group(2).strip(u'/').lower()
                if location in locations:
                    metadata['locationqid'] = locations.get(location)
                else:
                    if location not in missedlocations:
                        missedlocations[location]=0
                    missedlocations[location] += 1

                    metadata['locationqid'] = locations.get(location)
            elif location2Match:
                print (location2Match.group(1))
                location = location2Match.group(1).split(u',')[0].lower().replace(u' ', u'-')
                print (location)

                if location in locations:
                    print (u'Location found')
                    metadata['locationqid'] = locations.get(location)
                else:
                    if location not in missedlocations:
                        missedlocations[location]=0
                    missedlocations[location] += 1

                    metadata['locationqid'] = locations.get(location)

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            metadata['id'] = u'%s' % (match.group(1),)
            metadata['artworkidpid'] = u'P4373'
            metadata['artworkid'] = u'%s' % (match.group(1),)

            titleRegex = u'\<h2 class\=\"section-title\"\>([^\<]+)\<\/h2\>'
            titleMatch = re.search(titleRegex, itemPageData)

            if titleMatch:
                title = htmlparser.unescape(titleMatch.group(1)).strip()
            else:
                # Sometimes nothing is returned. Just sleep and continue with the next one
                pywikibot.output(u'No title found, probably something went wrong. Sleeping and skipping')
                time.sleep(60)
                continue
                #title = u'(without title)'

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                              }

            artistRegex = u'\<h3 class\=\"section-subtitle\"\>([^\<]+)\<\/h3\>'
            artistMatch = re.search(artistRegex, itemPageData)

            artistCleanupRegex = u'^(.+)\(([^\)]+)\)$'

            if artistMatch:
                dirtyname = htmlparser.unescape(artistMatch.group(1)).strip()
            else:
                dirtyname = u'anonymous'

            artistCleanupMatch = re.match(artistCleanupRegex, dirtyname)

            if artistCleanupMatch:
                name = artistCleanupMatch.group(1).strip()
            else:
                name = dirtyname.strip()

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                        u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                        }

            # Only match on years
            dateregex = u'\<h4\>Date\<\/h4\>[\r\n\t\s]*\<p\>\s*(\d\d\d\d)\s*(\(signed and dated\))?\<\/p\>'
            circadateregex = u'\<h4\>Date\<\/h4\>[\r\n\t\s]*\<p\>\s*circa (\d\d\d\d)\s*\<\/p\>'
            periodregex = u'\<h4\>Date\<\/h4\>[\r\n\t\s]*\<p\>\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)\s*\<\/p\>'
            circaperiodegex = u'\<h4\>Date\<\/h4\>[\r\n\t\s]*\<p\>\s*circa\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)\s*\<\/p\>'
            otherdateregex = u'\<h4\>Date\<\/h4\>[\r\n\t\s]*\<p\>\s*([^\<]+)\s*\<\/p\>'

            datematch = re.search(dateregex, itemPageData)
            circadatematch = re.search(circadateregex, itemPageData)
            periodmatch = re.search(periodregex, itemPageData)
            circaperiodmatch = re.search(circaperiodegex, itemPageData)
            otherdatematch = re.search(otherdateregex, itemPageData)

            if datematch:
                metadata['inception'] = htmlparser.unescape(datematch.group(1))
            elif circadatematch:
                metadata['inception'] = htmlparser.unescape(circadatematch.group(1))
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1),)
                metadata['inceptionend'] = int(periodmatch.group(2),)
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                metadata['inceptionend'] = int(circaperiodmatch.group(2))
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            mediumRegex = u'\<h4\>Materials\<\/h4\>[\r\n\t\s]*\<p\>Oil on canvas\<\/p\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch:
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'\<h4\>Measurements\<\/h4\>[\r\n\t\s]*\<p\>([^\<]+)\<\/p\>'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()
                regex_2d = u'^(?P<height>\d+)\s*(x|×)\s*(?P<width>\d+)\s*mm'
                regex_3d = u'^(?P<height>\d+)\s*(x|×)\s*(?P<width>\d+)\s*(x|×)\s*(?P<depth>\d+)\s*mm'
                match_2d = re.match(regex_2d, dimensiontext)
                match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = u'%s' % (float(match_2d.group(u'height'))/10, )
                    metadata['widthcm'] = u'%s' % (float(match_2d.group(u'width'))/10, )
                if match_3d:
                    metadata['heightcm'] = u'%s' % (float(match_3d.group(u'height'))/10, )
                    metadata['widthcm'] = u'%s' % (float(match_3d.group(u'width'))/10, )
                    metadata['depthcm'] = u'%s' % (float(match_3d.group(u'depth'))/10, )

            # Add genre
            genres = { u'Animals' : u'Q16875712',
                       u'Scenes of everyday life (genre)' : u'Q1047337',
                       u'History' : u'Q742333',
                       u'Landscape' : u'Q191163',
                       u'Portrait' : u'Q134307',
                       u'Religion' : u'Q2864737',
                       u'Townscape' : u'Q1935974',
                       u'Still Life' : u'Q170571',
                       u'Seascape' : u'Q158607',
                       }

            genresubjectregex = u'\<a href\=\"\/results\?Subject\=([^\"]+)\"\>([^\<]+)\<\/a\>'
            genresubjectmatches = re.finditer(genresubjectregex, itemPageData)

            if genresubjectmatches:
                for genresubjectmatch in genresubjectmatches:
                    if genresubjectmatch.group(2) in genres:
                        metadata[u'genreqid'] = genres.get(genresubjectmatch.group(2))
                        break
                    else:
                        print (u'Genre %s not found' % (genresubjectmatch.group(2),))

            if not metadata.get(u'genreqid'):
                genresummaryregex = u'\<h2\>Summary\<\/h2\>[\r\n\t\s]*\<p style\=\"white-space\: pre-line\"\>[^\<]*(Portrait of|three quarter length Portrait of|Framed portrait of|half-length portrait)[^\<]*\<\/p\>'
                genresummarymatch = re.search(genresummaryregex, itemPageData)
                if genresummarymatch:
                    metadata[u'genreqid'] = u'Q134307' # Portrait
                    print (u'Summary based portrait found')

            # Add place made
            places = { u'Amsterdam' : u'Q727',
                       u'Bologna' : u'Q1891',
                       u'Cambridge' : u'Q350',
                       u'China' : u'Q29520',
                       u'Denmark' : u'Q35',
                       u'Devon' : u'Q23156',
                       u'Dordrecht' : u'Q26421',
                       u'England' : u'Q21',
                       u'Flanders (Belgium from 1830)' : u'Q31',
                       u'Florence' : u'Q2044',
                       u'France' : u'Q142',
                       u'Germany' : u'Q183',
                       u'Great Britain' : u'Q23666',
                       u'Haarlem' : u'Q9920',
                       u'Holland' : u'Q102911',
                       u'Ireland' : u'Q22890',
                       u'Italy' : u'Q38',
                       u'Leiden' : u'Q43631',
                       u'London' : u'Q84',
                       u'Naples' : u'Q2634',
                       u'Netherlands' : u'Q55',
                       u'Paris' : u'Q90',
                       u'Rome' : u'Q220',
                       u'Scotland' : u'Q22',
                       u'Wales' : u'Q25',
                       u'Windsor' : u'Q464955',
                       u'Windsor Castle' : u'Q464955'
                       }

            placeregex = u'\<h4\>Place of origin\<\/h4\>[\s\t\r\n]*\<p\>([^\<]+)\<\/p\>'
            placematch = re.search(placeregex, itemPageData)
            if placematch:
                if placematch.group(1) in places:
                    metadata[u'madeinqid'] = places.get(placematch.group(1))
                else:
                    print (u'Place %s not found' % (placematch.group(1),))
                    if placematch.group(1) not in missedplaces:
                        missedplaces[placematch.group(1)]=0
                    missedplaces[placematch.group(1)] += 1

            # Image use policy unclear
            #imageMatch = re.search(imageregex, itemPageData)
            #if imageMatch:
            #    metadata[u'imageurl'] = imageMatch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            yield metadata
    pywikibot.output(u'Final list of missed locations')
    pywikibot.output(missedlocations)
    pywikibot.output(u'Final list of missed made in places')
    pywikibot.output(missedplaces)

def nationalTrustLocationsOnWikidata():
    '''
    Just return all the National Trust locations as a dict
    :return: Dict
    '''
    result = {}
    query = u"""SELECT ?item ?url WHERE {
  ?item wdt:P1602 ?artukid .
  ?item wdt:P973 ?url .
  FILTER regex (?artukid, "^national-trust") .
  } LIMIT 1000"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        identifier = resultitem.get('url').replace(u'https://www.nationaltrust.org.uk/', u'')
        result[identifier] = qid
    return result

def main():
    dictGen = getNTGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
