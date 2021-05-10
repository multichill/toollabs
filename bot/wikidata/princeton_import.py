#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Princeton Art Museum paintings.

Using https://artmuseum.princeton.edu/search/collections?results=2&typeList=%5B%22paintings%22%5D was has an api

Documented at https://github.com/Princeton-University-Art-Museum/puam-api-docs
"""
import artdatabot
import pywikibot
import requests
import re
from html.parser import HTMLParser

def getPrincetonGenerator():
    """
    Generator to return Princeton paintings
    :return:
    """
    searchurl = 'https://data.artmuseum.princeton.edu/objects?term=2052977&size=%s&from=%s'

    next_page = True
    size = 10
    i = 0
    htmlparser = HTMLParser()
    ulanartists = ulanArtistsOnWikidata()
    makers = {}
    #missedlocations = {}

    while next_page:
        searchpage = requests.get(searchurl % (size, i))
        searchjson =  searchpage.json().get('hits')
        i+=size

        # Check stop condition
        if i > searchjson.get('total'):
            next_page = False

        for itemsourceinfo in searchjson.get('hits'):
            iteminfo = itemsourceinfo.get('_source')

            # Will return a couple of other things?
            if not iteminfo.get('classification')=='Paintings':
                continue

            #import json
            #print (json.dumps(iteminfo, sort_keys=True, indent=4))


            metadata = {}
            metadata['instanceofqid'] = 'Q3305213'
            metadata['collectionqid'] = 'Q2603905'
            metadata['collectionshort'] = 'Princeton'
            metadata['locationqid'] = 'Q2603905'

            itemid = '%s' % (iteminfo.get('objectid'),)
            url = 'https://artmuseum.princeton.edu/collections/objects/%s' % (itemid,)
            print (url)
            metadata['url'] = url

            #metadata['artworkidpid'] = 'Pxxxx' # Maybe later?
            #metadata['artworkid'] = itemid
            metadata['idpid'] = 'P217'
            metadata['id'] = iteminfo.get('objectnumber')

            # Title is provided in three languages. Usually Swedish and English
            if iteminfo.get('displaytitle'):
                title = iteminfo.get('displaytitle').replace('\n', ' ').replace('\r', ' ')
                if len(title) > 220:
                    title = title[0:200]
                metadata['title'] = { 'en' : title.strip(' '),
                                      }
            if iteminfo.get('makers'):
                if len(iteminfo.get('makers')) > 0:
                    # Just only work on the first one
                    maker = iteminfo.get('makers')[0]
                    # Copies have other roles and get skipped now
                    if maker.get('role')=='Artist':
                        if maker.get('prefix'):
                            if maker.get('prefix')=='Attributed to':
                                name = maker.get('displayname')
                                metadata['description'] = {'en' : 'painting attributed to %s' % (name, ),
                                                           'nl' : 'schilderij toegeschreven aan %s' % (name, ),
                                                           }
                            else:
                                name = maker.get('displaymaker')
                                metadata['description'] = {'en' : 'painting %s' % (name, ),
                                                           }
                        elif maker.get('displayname')=='Anonymous':
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
                            makerid = maker.get('id')
                            if makerid in makers:
                                metadata['creatorqid'] = makers.get(makerid)
                            else:
                                makerpage = requests.get('https://data.artmuseum.princeton.edu/makers/%s' % (makerid,))
                                try:
                                    makerjson = makerpage.json()
                                    if makerjson.get('identifiers'):
                                        for identifier in makerjson.get('identifiers'):
                                            if identifier.get('source') == 'ULAN':
                                                if identifier.get('id') in ulanartists:
                                                    metadata['creatorqid'] = ulanartists.get(identifier.get('id'))
                                                    makers[makerid] = metadata['creatorqid']
                                                else:
                                                    print('Nothing found for ULAN id %s' % (identifier.get('id'),))
                                except ValueError:
                                    print('Maker %s not found' % (makerid,))
                            # Do actor lookup logic.
                            #if actor.get('links'):
                            #    for actorlink in actor.get('links'):
                            #        # The have Wikidata links!
                            #        if actorlink.get('link_type')=='WikiData':
                            #            metadata['creatorqid'] = actorlink.get('link').replace('http://www.wikidata.org/entity/', '')
                        metadata['creatorname'] = name.replace('\n', ' ').replace('\r', ' ').strip(' ')

            if iteminfo.get('displaydate'):
                dateregex = u'^(\d\d\d\d)$'
                datecircaregex = u'^ca\.\s*(\d\d\d\d)$'
                periodregex = u'^(\d\d\d\d)\s*-\s*(\d\d\d\d)$'
                shortperiodregex = u'^(\d\d)(\d\d)\s*[–-]\s*(\d\d)$'
                circaperiodregex = u'^ca\.\s*(\d\d\d\d)\s*[–-]\s*(\d\d\d\d)$'
                circashortperiodregex = u'^ca\.\s*(\d\d)(\d\d)\s*[–-]\s*(\d\d)$'
                circaveryshortperiodregex = u'^ca\.\s*(\d\d\d)(\d)\s*[–-]\s*(\d)$'

                datematch = re.search(dateregex, iteminfo.get('displaydate'), flags=re.IGNORECASE)
                datecircamatch = re.search(datecircaregex, iteminfo.get('displaydate'), flags=re.IGNORECASE)
                periodmatch = re.search(periodregex, iteminfo.get('displaydate'), flags=re.IGNORECASE)
                shortperiodmatch = re.search(shortperiodregex, iteminfo.get('displaydate'), flags=re.IGNORECASE)
                circaperiodmatch = re.search(circaperiodregex, iteminfo.get('displaydate'), flags=re.IGNORECASE)
                circashortperiodmatch = re.search(circashortperiodregex, iteminfo.get('displaydate'), flags=re.IGNORECASE)
                circaveryshortperiodmatch = re.search(circaveryshortperiodregex, iteminfo.get('displaydate'), flags=re.IGNORECASE)

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
                    print (u'Could not parse date: "%s"' % (iteminfo.get('displaydate'),))

            # Sometimes provided
            if iteminfo.get('accessionyear'):
                acquisitionregex = '^(\d\d\d\d)-01-01$'
                acquisitionmatch = re.match(acquisitionregex, iteminfo.get('accessionyear'))
                if acquisitionmatch:
                    metadata['acquisitiondate'] = int(acquisitionmatch.group(1))

            if iteminfo.get('medium') and iteminfo.get('medium')=='Oil on canvas':
                metadata['medium'] = u'oil on canvas'

            if iteminfo.get('dimensionelements'):
                for dimensionelement in iteminfo.get('dimensionelements'):
                    if dimensionelement.get('element') == 'Overall' and dimensionelement.get('units') == 'centimeters':
                        # FIXME: Artdatabot assumes string. That's probably not correct
                        if dimensionelement.get('type') == 'Height':
                            metadata['heightcm'] = dimensionelement.get('dimension')
                        elif dimensionelement.get('type') == 'Width':
                            metadata['widthcm'] = dimensionelement.get('dimension')

            culture = None
            if iteminfo.get('terms'):
                terms = []
                for term in iteminfo.get('terms'):
                    if term.get('termtype') == 'Culture':
                        culture = term.get('term')
                    elif term.get('termtype') == 'Subject':
                        terms.append(term.get('term'))

                # TODO: Do something with culture here. Country is sometimes available

                if 'religious art' in terms:
                    metadata['genreqid'] = 'Q2864737' # religious art
                elif 'mythology' in terms:
                    metadata['genreqid'] = 'Q3374376' # mythological painting
                elif 'portraits' in terms:
                    metadata['genreqid'] = 'Q134307' # portrait
                elif 'seascapes' in terms:
                    metadata['genreqid'] = 'Q158607' # marine art
                elif 'landscapes (representations)' in terms:
                    metadata['genreqid'] = 'Q191163' # landscape art

            # Figure out later
            if iteminfo.get('geography'):
                geography = iteminfo.get('geography')[0]
                if geography.get('city'):
                    if geography.get('city') == 'New York':
                        metadata['madeinqid'] = 'Q60'
                    else:
                        print('Unknown city %s' % (geography.get('city'),))
                elif geography.get('country'):
                    if geography.get('country') == 'United States':
                        metadata['madeinqid'] = 'Q30'
                    elif geography.get('country') == 'China':
                        metadata['madeinqid'] = 'Q29520'
                    elif geography.get('country') == 'Japan':
                        metadata['madeinqid'] = 'Q17'
                    else:
                        print('Unknown country %s' % (iteminfo.get('country'),))
            elif culture:
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
                else:
                    print('Unknown culture %s' % (culture,))

            if iteminfo.get('hasimage') and iteminfo.get('hasimage') =='true':
                metadata['iiifmanifesturl'] = 'https://data.artmuseum.princeton.edu/iiif/objects/%s' % (itemid,)
                if iteminfo.get('media'):
                    media = iteminfo.get('media')[0]
                    if media.get('restrictions') == None:
                        metadata['imageurl'] = '%s/full/full/0/default.jpg' % (media.get('uri'),)
                        metadata['imageurlformat'] = u'Q2195' #JPEG
                        #    metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
                        metadata['imageoperatedby'] = u'Q2603905'
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
    dictGen = getPrincetonGenerator()
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
