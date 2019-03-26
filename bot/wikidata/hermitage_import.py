#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import Hermitage paintings. Second iteration, they have an api now:

https://www.hermitagemuseum.org/api/v10/search?resultLang=en&queryLang=en&collection=mainweb|kamis|rooms|hermitage&query=meta_woa_category_main:(%22Painting%22)&pageSize=10&page=1&output=application/json

"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser
import time

def getHermitageGenerator():
    '''
    Generator to return Hermitage paintings
    '''

    # Use one session for everything
    # session = requests.Session()

    # They broke it
    # https://www.hermitagemuseum.org/api/v10/search?resultLang=en&queryLang=en&collection=mainweb|kamis|rooms|hermitage&query=meta_woa_category_main:(%22Painting%22)%20AND%20meta_authoring_template:(%22WOA%22)&pageSize=100&page=1&output=application/json

    # 1 - 367
    #searchBaseUrl = u'https://www.hermitagemuseum.org/wps/portal/hermitage/explore/collections/col-search/?lng=en&p1=category:%%22Painting%%22&p15=%s'
    basesearchurl = u'https://www.hermitagemuseum.org/api/v10/search?resultLang=en&queryLang=en&collection=mainweb|kamis|rooms|hermitage&query=meta_woa_category_main:(%%22Painting%%22)%%20AND%%20meta_authoring_template:(%%22WOA%%22)&pageSize=100&page=%s&output=application/json'
    #baseUrl = u'https://www.hermitagemuseum.org%s'
    htmlparser = HTMLParser.HTMLParser()

    # 6575, 100 per page

    foundids = []

    for i in range(1, 67):
        searchUrl = basesearchurl % (i,)
        print searchUrl
        searchPage = requests.get(searchUrl, verify=False)
        searchJson = searchPage.json()

        for iteminfo in searchJson.get('es_apiResponse').get('es_result'):
            metadata = {}

            metadata['collectionqid'] = u'Q132783'
            metadata['collectionshort'] = u'Hermitage'
            metadata['locationqid'] = u'Q132783'
            metadata['instanceofqid'] = u'Q3305213'

            # metadata['artworkidpid'] = u'Pxxxx' maybe in the future
            metadata['artworkid'] = iteminfo.get('es_title')

            if iteminfo.get('es_title') in foundids:
                print u'1Ran into the same id %s again!' % (iteminfo.get('es_title'),)
                print u'2Ran into the same id %s again!' % (iteminfo.get('es_title'),)
                print u'3Ran into the same id %s again!' % (iteminfo.get('es_title'),)
                print u'4Ran into the same id %s again!' % (iteminfo.get('es_title'),)
                print u'5Ran into the same id %s again!' % (iteminfo.get('es_title'),)
                print u'6Ran into the same id %s again!' % (iteminfo.get('es_title'),)
                print u'7Ran into the same id %s again!' % (iteminfo.get('es_title'),)
                continue

            foundids.append(iteminfo.get('es_title'))
            
            metadata['url'] = u'https://www.hermitagemuseum.org/wps/portal/hermitage/digital-collection/01.+Paintings/%s/' % (iteminfo.get('es_title'),)

            fields = {}

            for field in iteminfo.get('ibmsc_field'):
                fields[field.get('id')] = field.get('#text')

            # In some rare cases we have no inventory number. Skip these.
            if not fields.get('meta_woa_inventory'):
                continue

            metadata['idpid'] = u'P217'
            metadata['id'] = fields.get('meta_woa_inventory')

            if fields.get('meta_woa_name'):
                title = fields.get('meta_woa_name')
                # Chop chop, several very long titles
                if len(title) > 220:
                    title = title[0:200].strip(' ')
                metadata['title'] = { u'en' : title,
                                      }

            name = fields.get('meta_woa_author_rubr')
            if name:
                regexnamedate = u'^([^,]+), (.+)\.\s*(c\.)?\s*\d\d\d\d-\d\d\d\d$'
                namematch = re.match(regexnamedate, name)
                if namematch:
                    name = u'%s %s' % (namematch.group(2), namematch.group(1),)
                    metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                                u'en' : u'painting by %s' % (name, ),
                                                u'de' : u'Gemälde von %s' % (name, ),
                                                u'fr' : u'peinture de %s' % (name, ),
                                                }
                else:
                    # Don't want to have to do clean up in multiple languages
                    metadata['description'] = { u'en' : u'painting by %s' % (name, ),
                                                }
            else:
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }

            if fields.get('meta_woa_date') and fields.get('meta_woa_date_low') and fields.get('meta_woa_date_high'):
                datecircaregex = u'^Circa (\d\d\d\d)$'
                datecircamatch = re.match(datecircaregex, fields.get('meta_woa_date'))
                if datecircamatch:
                    metadata['inception'] = datecircamatch.group(1).strip()
                    metadata['inceptioncirca'] = True
                elif fields.get('meta_woa_date')==fields.get('meta_woa_date_low') and fields.get('meta_woa_date')==fields.get('meta_woa_date_high'):
                    metadata['inception'] = fields.get('meta_woa_date')
                elif fields.get('meta_woa_date_low')!=fields.get('meta_woa_date_high'):
                    metadata['inceptionstart'] = int(fields.get('meta_woa_date_low'))
                    metadata['inceptionend'] = int(fields.get('meta_woa_date_high'))

            if fields.get('meta_woa_prvnc'):
                acqdateregex = u'^Entered the Hermitage in (\d\d\d\d)\;.*'
                acqdatamatch = re.match(acqdateregex, fields.get('meta_woa_prvnc'))
                if acqdatamatch:
                    metadata['acquisitiondate'] = acqdatamatch.group(1)

            if fields.get('meta_woa_material')==u'canvas' and fields.get('meta_woa_technique')==u'oil':
                metadata['medium'] = u'oil on canvas'

            if fields.get('meta_woa_dimension'):
                measurementstext = fields.get('meta_woa_dimension')
                regex_2d = u'^(?P<height>\d+(,\d+)?)\s*x\s*(?P<width>\d+(,\d+)?)\s*cm$'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            yield metadata


def main():
    dictGen = getHermitageGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
