#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Berlinische Galerie to Wikidata.

Use the Deutsche Digitale Bibliothek API

"""
import artdatabot
import pywikibot
import requests
import json
import pywikibot.data.sparql
import re

def gndOnWikidata():
    '''
    Just return all the GND people as a dict
    :return: Dict
    '''
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item wdt:P227 ?id . ?item wdt:P31 wd:Q5 } LIMIT 10000003'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result

def getBerlinischeGalerieGenerator(apikey):
    """
    Generator to return Groninger Museum paintings

    
    """
    # https://api.deutsche-digitale-bibliothek.de/search?oauth_consumer_key=tT2FYyDb72vzp2ag3vwCzc8rqk14zk6956JJ6tCE1kpJL1Ay5Yu1517160209130%20&query=provider%3A(Berlinische+OR+Galerie)
    # https://api.deutsche-digitale-bibliothek.de/items/B5MVYZFQZPREC45XIVWWEUGRXKF2FDJT/aip?oauth_consumer_key=tT2FYyDb72vzp2ag3vwCzc8rqk14zk6956JJ6tCE1kpJL1Ay5Yu1517160209130
    # Accept JSON something

    offset = 15000

    basesearchurl = u'https://api.deutsche-digitale-bibliothek.de/search?oauth_consumer_key=%s&query=provider%%3A(Berlinische+OR+Galerie)&offset=%s'
    baseitemurl = u'https://api.deutsche-digitale-bibliothek.de/items/%s/aip?oauth_consumer_key=%s'

    gndids = gndOnWikidata()
    missedgndids = {}

    i = 0
    while True:
        searchurl = basesearchurl % (apikey, offset,)

        searchPage = requests.get(searchurl)
        searchJson = searchPage.json()

        numberberOfDocs = searchJson.get(u'results')[0].get(u'numberOfDocs')
        if numberberOfDocs==0:
            # We're done
            print missedgndids
            return
        offset = offset + numberberOfDocs

        for record in searchJson.get(u'results')[0].get(u'docs'):
            if not record.get(u'subtitle') == u'Gemälde':
                continue
            i = i + 1
            metadata = {}
            itemid = record.get(u'id')
            itemurl = baseitemurl % (itemid, apikey)
            print itemurl
            itemPage = requests.get(itemurl)
            itemJson = itemPage.json()
            #print json.dumps(itemJson, indent=4, sort_keys=True)

            metadata['refurl'] = u'https://www.deutsche-digitale-bibliothek.de/item/%s' % (itemid,)
            metadata['url'] = itemJson.get(u'edm').get(u'RDF').get(u'Aggregation').get(u'isShownAt').get(u'@resource')

            metadata['collectionqid'] = u'Q700222'
            metadata['collectionshort'] = u'BG'
            metadata['locationqid'] = u'Q700222'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID.
            metadata['id'] = itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'identifier').replace(u' (Inventarnummer)', u'').replace(u'\n', u'')
            metadata['idpid'] = u'P217'

            title = itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'title')

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'de' : title,
                                }
            agent = itemJson.get(u'edm').get(u'RDF').get(u'Agent')
            gndid = False
            name = u''
            if type(agent) is dict:
                gndid = agent.get(u'@about').replace(u'http://d-nb.info/gnd/', u'')
                name = agent.get(u'prefLabel')
            if type(itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'creator')) is list:
                name = itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'creator')[0].replace(u' (Herstellung)', u'')
                name = name + u' ' + itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'creator')[0].replace(u' (Herstellung)', u'(multiple creators)')
            else:
                # This will be slightly messed up
                name = itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'creator').replace(u' (Herstellung)', u'')

            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            if gndid in gndids:
                print u'Found GND id %s on %s' % (gndid, gndids.get(gndid))
                metadata['creatorqid'] = gndids.get(gndid)
            else:
                print u'Did not find id %s' % (gndid,)
                if gndid not in missedgndids:
                    missedgndids[gndid] = 0
                missedgndids[gndid] = missedgndids[gndid] + 1

            metadata['description'] = { u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        }

            # FIXME : This will only catch oil on canvas
            if itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'format')==u'Öl auf Leinwand (Material/Technik)':
                metadata['medium'] = u'oil on canvas'

            inception = itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'created')
            if inception:
                metadata['inception'] = inception.replace(u' (Herstellung)', u'')

            dimensionslist = itemJson.get(u'edm').get(u'RDF').get(u'ProvidedCHO').get(u'extent')
            if dimensionslist:
                if type(dimensionslist) is list:
                    dimensions = dimensionslist[0]
                else:
                    dimensions = dimensionslist

                regex_2d = u'^Bildmaß:\s*(?P<height>\d+(\,\d+)?)\s*(x|×)\s*(?P<width>\d+(\,\d+)?)\s*cm\s*'
                #regex_3d = u'.*\((?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) (x|×) (?P<depth>\d+(\.\d+)?) cm\)'
                match_2d = re.match(regex_2d, dimensions)
                # match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                #elif match_3d:
                #metadata['heightcm'] = match_3d.group(u'height')
                #metadata['widthcm'] = match_3d.group(u'width')
                #metadata['depthcm'] = match_3d.group(u'depth')

            webresource = itemJson.get(u'edm').get(u'RDF').get(u'WebResource')

            if webresource:
                if type(webresource.get(u'rights')) is dict:
                    rights = webresource.get(u'rights').get(u'@resource')
                    if rights == u'http://creativecommons.org/publicdomain/zero/1.0/':
                        metadata[u'imageurl'] = webresource.get(u'@about').replace(u'resolution=highImageResolution', u'resolution=superImageResolution')
                        metadata[u'imageurlformat'] = u'Q2195' #JPEG
                        metadata[u'imageurllicense'] = u'Q6938433' # cc-zero

            yield metadata
    
def main():
    # FIXME: Commandline argument
    apikey = u'topsecret'
    dictGen = getBerlinischeGalerieGenerator(apikey)

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
