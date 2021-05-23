#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Harvard Art Museums paintings.

For humans at https://harvardartmuseums.org/collections?classification%5B%5D=Paintings

For bots at https://api.harvardartmuseums.org/object?classification=Paintings&apikey=c1c77150-6ae1-11e9-b77e-1ff5638001eb

Documented at https://github.com/harvardartmuseums/api-docs
"""
import artdatabot
import pywikibot
import requests
import re
from html.parser import HTMLParser

def getHarvardGenerator():
    """
    Generator to return Harvard paintings
    :return:
    """
    searchurl = 'https://api.harvardartmuseums.org/object?classification=Paintings&apikey=c1c77150-6ae1-11e9-b77e-1ff5638001eb&page=%s'

    next_page = True
    i = 0
    htmlparser = HTMLParser()
    ulanartists = ulanArtistsOnWikidata()
    makers = {}
    #missedlocations = {}

    while next_page:
        print (searchurl % (i,))
        searchpage = requests.get(searchurl % (i,))
        searchjson = searchpage.json()
        i+=1

        # Do we have a next page to work on?
        if not searchjson.get('info').get('next'):
            next_page = False

        for iteminfo in searchjson.get('records'):

            # Will return a couple of other things?
            if not iteminfo.get('classification')=='Paintings':
                continue

            #import json
            #print (json.dumps(iteminfo, sort_keys=True, indent=4))

            metadata = {}
            metadata['instanceofqid'] = 'Q3305213'
            metadata['collectionqid'] = 'Q3783572'
            metadata['collectionshort'] = 'Harvard'
            metadata['locationqid'] = 'Q3783572'

            itemid = '%s' % (iteminfo.get('objectid'),)
            url = iteminfo.get('url')
            print (url)
            metadata['url'] = url
            metadata['describedbyurl'] = 'https://hvrd.art/o/%s' % (itemid,)

            #metadata['artworkidpid'] = 'Pxxxx' # Maybe later?
            #metadata['artworkid'] = itemid
            metadata['idpid'] = 'P217'
            metadata['id'] = iteminfo.get('objectnumber')

            # Title is provided in three languages. Usually Swedish and English
            if iteminfo.get('title'):
                title = iteminfo.get('title').replace('\n', ' ').replace('\r', ' ')
                if len(title) > 220:
                    title = title[0:200]
                metadata['title'] = { 'en' : title.strip(' '),
                                      }
            if iteminfo.get('people'):
                if len(iteminfo.get('people')) > 0:
                    # Just only work on the first one
                    maker = iteminfo.get('people')[0]
                    # Copies have other roles and get skipped now
                    if maker.get('role')=='Artist':
                        if maker.get('prefix'):
                            if maker.get('prefix')=='Attributed to':
                                name = maker.get('name')
                                metadata['description'] = {'en' : 'painting attributed to %s' % (name, ),
                                                           'nl' : 'schilderij toegeschreven aan %s' % (name, ),
                                                           }
                            else:
                                name = maker.get('displayname')
                                metadata['description'] = {'en' : 'painting %s' % (name, ),
                                                           }
                        elif maker.get('displayname')=='Anonymous' or maker.get('displayname')=='Unknown Artist':
                            name = 'anonymous'
                            metadata['description'] = { 'nl' : 'schilderij van anonieme schilder',
                                                        'en' : 'painting by anonymous painter',
                                                        }
                            metadata['creatorqid'] = 'Q4233718'
                        else:
                            name = maker.get('displayname')
                            metadata['description'] = { 'nl' : 'schilderij van %s' % (name, ),
                                                        'en' : 'painting by %s' % (name, ),
                                                        'de' : 'Gemälde von %s' % (name, ),
                                                        'fr' : 'peinture de %s' % (name, ),
                                                        }
                            makerid = maker.get('personid')
                            if makerid in makers:
                                metadata['creatorqid'] = makers.get(makerid)
                            else:
                                makerpage = requests.get('https://api.harvardartmuseums.org/person/%s?apikey=c1c77150-6ae1-11e9-b77e-1ff5638001eb' % (makerid,))
                                try:
                                    makerjson = makerpage.json()
                                    if makerjson.get('ulan_id'):
                                        if makerjson.get('ulan_id') in ulanartists:
                                            metadata['creatorqid'] = ulanartists.get(makerjson.get('ulan_id'))
                                            makers[makerid] = metadata['creatorqid']
                                        else:
                                            print('Nothing found for ULAN id %s' % (makerjson.get('ulan_id'),))
                                        # They also have viaf and wikipedia_id (page id on enwp)
                                except ValueError:
                                    print('Maker %s not found' % (makerid,))
                            # Do actor lookup logic.
                            #if actor.get('links'):
                            #    for actorlink in actor.get('links'):
                            #        # The have Wikidata links!
                            #        if actorlink.get('link_type')=='WikiData':
                            #            metadata['creatorqid'] = actorlink.get('link').replace('http://www.wikidata.org/entity/', '')
                        metadata['creatorname'] = name.replace('\n', ' ').replace('\r', ' ').strip(' ')

            # It's dated, but they also have datebegin and dateend
            if iteminfo.get('dated') and not iteminfo.get('dated')=='None':
                dateregex = u'^(\d\d\d\d)$'
                datecircaregex = u'^c\.\s*(\d\d\d\d)$'
                periodregex = u'^(\d\d\d\d)\s*-\s*(\d\d\d\d)$'
                shortperiodregex = u'^(\d\d)(\d\d)\s*[–-]\s*(\d\d)$'
                circaperiodregex = u'^c\.\s*(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)$'
                circashortperiodregex = u'^c\.\s*(\d\d)(\d\d)\s*[–-]\s*(\d\d)$'
                circaveryshortperiodregex = u'^c\.\s*(\d\d\d)(\d)\s*[–-]\s*(\d)$'

                datematch = re.search(dateregex, iteminfo.get('dated'), flags=re.IGNORECASE)
                datecircamatch = re.search(datecircaregex, iteminfo.get('dated'), flags=re.IGNORECASE)
                periodmatch = re.search(periodregex, iteminfo.get('dated'), flags=re.IGNORECASE)
                shortperiodmatch = re.search(shortperiodregex, iteminfo.get('dated'), flags=re.IGNORECASE)
                circaperiodmatch = re.search(circaperiodregex, iteminfo.get('dated'), flags=re.IGNORECASE)
                circashortperiodmatch = re.search(circashortperiodregex, iteminfo.get('dated'), flags=re.IGNORECASE)
                circaveryshortperiodmatch = re.search(circaveryshortperiodregex, iteminfo.get('dated'), flags=re.IGNORECASE)

                if datematch:
                    metadata['inception'] = int(datematch.group(1))
                elif datecircamatch:
                    metadata['inception'] = int(datecircamatch.group(1))
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1),)
                    metadata['inceptionend'] = int(periodmatch.group(2),)
                elif shortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                    metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                    metadata['inceptioncirca'] = True
                elif circashortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                    metadata['inceptioncirca'] = True
                elif circaveryshortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (circaveryshortperiodmatch.group(1),circaveryshortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (circaveryshortperiodmatch.group(1),circaveryshortperiodmatch.group(3),))
                    metadata['inceptioncirca'] = True
                else:
                    print (u'Could not parse date: "%s"' % (iteminfo.get('dated'),))

            # Sometimes provided and it's an integer
            if iteminfo.get('accessionyear'):
                metadata['acquisitiondate'] = int(iteminfo.get('accessionyear'))

            # Add extra collection based on the credit line
            if iteminfo.get('creditline'):
                if iteminfo.get('creditline').startswith('Harvard Art Museums/Fogg Museum'):
                    metadata['extracollectionqid'] = 'Q809600'
                    #metadata['locationqid'] = 'Q809600' # Overwrite location with Fogg? Looks like one big building
                elif iteminfo.get('creditline').startswith('Harvard Art Museums/Busch-Reisinger Museum'):
                    metadata['extracollectionqid'] = 'Q1017269'
                    #metadata['locationqid'] = 'Q1017269' # Overwrite location with Busch-Reisinger? Looks like one big building
                elif iteminfo.get('creditline').startswith('Harvard Art Museums/Arthur M. Sackler Museum'):
                    metadata['extracollectionqid'] = 'Q2493390'
                    # No location overwrite here.
                # Add the extra inventory number if needed
                if metadata.get('extracollectionqid'):
                    metadata['extraid'] = iteminfo.get('objectnumber')

            # leave it for artdatabot to sort out "oil on canvas"
            if iteminfo.get('medium'):
                metadata['medium'] = iteminfo.get('medium')

            if iteminfo.get('dimensions'):
                regex_2d = '^(H\.)?\s*(?P<height>\d+(\.\d+)?)\s*x\s*(W\.)?\s*(?P<width>\d+(\.\d+)?)\s*cm.*$'
                match_2d = re.match(regex_2d, iteminfo.get('dimensions'))
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')

            # No information about the genre found

            # Only culture in the api, place seems to be missing
            if iteminfo.get('culture'):
                culture = iteminfo.get('culture')
                if culture=='Chinese':
                    metadata['madeinqid'] = 'Q29520'
                elif culture=='American':
                    metadata['madeinqid'] = 'Q30'
                elif culture=='Italian':
                    metadata['madeinqid'] = 'Q38'
                elif culture=='Japanese':
                    metadata['madeinqid'] = 'Q17'
                elif culture=='French':
                    metadata['madeinqid'] = 'Q142'
                elif culture=='British':
                    metadata['madeinqid'] = 'Q145'
                elif culture=='Mexican':
                    metadata['madeinqid'] = 'Q96'
                elif culture=='German':
                    metadata['madeinqid'] = 'Q183'
                elif culture=='Dutch':
                    metadata['madeinqid'] = 'Q55'
                elif culture=='Flemish':
                    metadata['madeinqid'] = 'Q234'
                elif culture=='Spanish':
                    metadata['madeinqid'] = 'Q29'
                elif culture=='Greek':
                    metadata['madeinqid'] = 'Q41'
                elif culture=='Russian':
                    metadata['madeinqid'] = 'Q159'
                elif culture=='Egyptian (ancient)':
                    metadata['madeinqid'] = 'Q79'
                elif culture=='Europe':
                    metadata['madeinqid'] = 'Q46'
                elif culture=='Korean':
                    metadata['madeinqid'] = 'Q18097'
                elif culture=='Indian':
                    metadata['madeinqid'] = 'Q668'
                else:
                    print('Unknown culture %s' % (culture,))

            # IIIF
            if iteminfo.get('seeAlso'):
                if iteminfo.get('seeAlso')[0].get('type') == 'IIIF Manifest':
                    metadata['iiifmanifesturl'] = iteminfo.get('seeAlso')[0].get('id')

            # Nice images
            if not iteminfo.get('copyright') and iteminfo.get('primaryimageurl'):
                metadata['imageurl'] = iteminfo.get('primaryimageurl')
                metadata['imageurlformat'] = 'Q2195' #JPEG
                #    metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
                metadata['imageoperatedby'] = 'Q3783572'
                metadata['imageurlforce'] = False
            yield metadata

    #for missedlocation in sorted(missedlocations, key=missedlocations.get):
    #    print('* %s - %s' % (missedlocation, missedlocations.get(missedlocation),))

def ulanArtistsOnWikidata():
    """
    Just return all the ULAN people as a dict
    :return: Dict
    """
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:P245 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
        result[resultitem.get('id')] = qid
    return result

def main(*args):
    dictGen = getHarvardGenerator()
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
