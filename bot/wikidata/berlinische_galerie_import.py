#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Berlinische Galerie to Wikidata.

They seems to use Emuseum with json output

This bot uses artdatabot to upload it to Wikidata.

First version used the Deutsche Digitale Bibliothek API

"""
import artdatabot
import pywikibot
import requests
import re

def get_berlinische_galerie_generator():
    """
    Generator to return Berlinische Galerie paintings
    """
    base_search_url = 'https://sammlung-online.berlinischegalerie.de/solr/published/select?&fq=type:Object&fq=loans_b:%%22false%%22&fq={!tag=et_classification_en_s}classification_en_s:(%%22Painting%%22)&q=*:*&rows=%s&sort=person_sort_en_s%%20asc&start=%s'

    start_url = base_search_url % (1, 0, )

    session = requests.Session()
    start_page = session.get(start_url)
    number_found = start_page.json().get('response').get('numFound')

    # Trying to hide the json with a build id that changes
    collection_page = session.get('https://sammlung-online.berlinischegalerie.de/en/collection/')
    build_id_regex = '<script id="__NEXT_DATA__" type="application/json">.+"buildId":"([^"]+)","isFallback":false,"gsp":true,"scriptLoader":\[\]}</script>'
    build_id_match = re.search(build_id_regex, collection_page.text)
    build_id = build_id_match.group(1)

    step = 10

    for i in range(0, number_found + step, step):
        search_url = base_search_url % (step, i,)

        print(search_url)
        search_page = session.get(search_url)

        for object_docs in search_page.json().get('response').get('docs'):
            metadata = {}
            object_id = object_docs.get('oid')

            url = 'https://sammlung-online.berlinischegalerie.de/en/collection/item/%s/' % (object_id, )
            json_url = 'https://sammlung-online.berlinischegalerie.de/_next/data/%s/en/collection/item/%s.json' % (build_id, object_id, )

            pywikibot.output(url)
            pywikibot.output(json_url)

            json_page = session.get(json_url)
            item_json = json_page.json().get('pageProps').get('data').get('item')
            metadata['url'] = url

           ## Add the identifier property
            metadata['artworkidpid'] = 'P13197'  # Berlinische Galerie object ID (P13197)
            metadata['artworkid'] = object_id

            # Only paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'
            metadata['id'] = item_json.get('ObjMainObjectNumberTxt')

            metadata['collectionqid'] = 'Q700222'
            metadata['collectionshort'] = 'BG'
            metadata['locationqid'] = 'Q700222'

            title = item_json.get('ObjTitleTxt').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('  ', ' ').strip()

            # Chop chop, might have long titles
            if len(title) > 220:
                title = title[0:200]
            title = title.replace('\t', '').replace('\n', '')
            metadata['title'] = {'de': title, }

            creator_name = item_json.get('ObjMainPersonTxt')

            if creator_name:
                if creator_name.lower() == 'unbekannt':
                    metadata['description'] = { 'de': '%s von %s' % ('Gemälde', creator_name, ),
                                                }
                else:
                    metadata['description'] = { 'nl': '%s van %s' % ('schilderij', creator_name,),
                                                'en': '%s by %s' % ('painting', creator_name,),
                                                'de': '%s von %s' % ('Gemälde', creator_name, ),
                                                'fr': '%s de %s' % ('peinture', creator_name, ),
                                                }
                metadata['creatorname'] = creator_name

            date = item_json.get('ObjDateTxt')

            if date:
                year_regex = '^\s*(\d\d\d\d)\s*$'
                date_circa_regex = '^um\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[\-\–\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^ca?\.\s*(\d\d\d\d)\s*[\-\–\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[\-\–\/](\d\d)$'
                circa_short_period_regex = '^ca?\.\s*(\d\d)(\d\d)[\-\–\/](\d\d)$'

                year_match = re.match(year_regex, date)
                date_circa_match = re.match(date_circa_regex, date)
                period_match = re.match(period_regex, date)
                circa_period_match = re.match(circa_period_regex, date)
                short_period_match = re.match(short_period_regex, date)
                circa_short_period_match = re.match(circa_short_period_regex, date)

                if year_match:
                    # Don't worry about cleaning up here.
                    metadata['inception'] = int(year_match.group(1))
                elif date_circa_match:
                    metadata['inception'] = int(date_circa_match.group(1))
                    metadata['inceptioncirca'] = True
                elif period_match:
                    metadata['inceptionstart'] = int(period_match.group(1),)
                    metadata['inceptionend'] = int(period_match.group(2),)
                elif circa_period_match:
                    metadata['inceptionstart'] = int(circa_period_match.group(1),)
                    metadata['inceptionend'] = int(circa_period_match.group(2),)
                    metadata['inceptioncirca'] = True
                elif short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(2), ))
                    metadata['inceptionend'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(3), ))
                elif circa_short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(2), ))
                    metadata['inceptionend'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(3), ))
                    metadata['inceptioncirca'] = True
                else:
                    print('Could not parse date: "%s"' % (date,))

            # acquisition year
            acquisition_year = item_json.get('ObjAcquisitionTxt')
            if acquisition_year:
                metadata['acquisitiondate'] = acquisition_year

            materials = item_json.get('ObjMaterialTxt_de')
            if materials:
                materials = materials.lower()
                material_lookup = {'acryl auf leinwand': 'oil on canvas' ,
                                   'öl auf leinwand': 'acrylic on canvas',}
                if materials in material_lookup:
                    metadata['medium'] = material_lookup.get(materials)
                else:
                    metadata['medium'] = materials.lower()

            owner = item_json.get('ObjOwnerTxt')
            if owner and owner == 'Berlinische Galerie, Landesmuseum für Moderne Kunst, Fotografie und Architektur, Berlin':
                metadata['ownerqid'] = 'Q700222'

            yield metadata
            continue

            # The provide free images. Just have to filter out the ones that are copyrighted
            default_image = item_json.get('DefaultImage')

            if default_image:
                for multimedia_item in item_json.get('ObjMultimediaMainImageRef').get('Items'):
                    if not multimedia_item.get('MulPhotocreditTxt'):
                        multimedia_image = multimedia_item.get('Multimedia')[0]
                        if multimedia_image.get('def') == "true":
                            if multimedia_image.get('mime') == 'image/jpeg':
                                metadata['imageurl'] = 'https://collection.kunsthaus.ch/%s' % (multimedia_image.get('extra'))
                                metadata['imageurlformat'] = 'Q27996264'  # JPEG
                                metadata['imageoperatedby'] = 'Q685038'
                                # Can use this to add suggestions everywhere
                                metadata['imageurlforce'] = True

            credit_line = item_json.get('ObjOwnerTxt')

            if credit_line and credit_line == 'Emil Bührle Collection, on long term loan at Kunsthaus Zürich':
                metadata['extracollectionqid'] = 'Q666331'

            yield metadata

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
            print (missedgndids)
            return
        offset = offset + numberberOfDocs

        for record in searchJson.get(u'results')[0].get(u'docs'):
            if not record.get(u'subtitle') == u'Gemälde':
                continue
            i = i + 1
            metadata = {}
            itemid = record.get(u'id')
            itemurl = baseitemurl % (itemid, apikey)
            print (itemurl)
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
                print (u'Found GND id %s on %s' % (gndid, gndids.get(gndid)))
                metadata['creatorqid'] = gndids.get(gndid)
            else:
                print (u'Did not find id %s' % (gndid,))
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

def main(*args):
    dict_gen = get_berlinische_galerie_generator()
    dry_run = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dry_run = True
        elif arg.startswith('-create'):
            create = True

    if dry_run:
        for painting in dict_gen:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()


if __name__ == "__main__":
    main()
