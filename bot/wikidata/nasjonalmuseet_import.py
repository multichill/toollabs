#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from National Museum of Art, Architecture and Design.
Minimal implementation to just get the free images.

Loop over https://www.nasjonalmuseet.no/en/collection/search/?type=painting

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import json
import re
from html.parser import HTMLParser

def getNasjonalmuseetGenerator():
    """
    Generator to return Nasjonalmuseet paintings
    """
    searchurl = 'https://www.nasjonalmuseet.no/en/collection/search//search?type=painting'
    htmlparser = HTMLParser()

    # We're using one session to get everything
    session = requests.Session()
    session.get(searchurl)

    for i in range(1, 200):
        postjson = { "includeRelatedResult": "false",
                     "page": "%s" % (i,),
                     }
        pywikibot.output ('%s page %s' % (searchurl, i))
        searchPage = requests.post(searchurl, data=postjson)
        # Double encoded json? Really?
        searchjson = json.loads(searchPage.json())

        #print (json.dumps(searchjson, indent=4, sort_keys=True))

        for iteminfo in searchjson.get('Results'):
            # Norway has discovered SSL
            url = 'https://www.nasjonalmuseet.no/%s' % iteminfo.get('url')
            print (json.dumps(iteminfo, indent=4, sort_keys=True))
            pywikibot.output (url)

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = 'Q1132918'
            metadata['collectionshort'] = 'Nasjonalmuseet'
            metadata['locationqid'] = 'Q1132918'

            # Search is for paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            if iteminfo.get('media').get('nmId'):
                metadata['id'] = iteminfo.get('media').get('nmId')
            else:
                print('Inventory number missing. Skipping')
                continue

            # Could probably get per item json too, but not needed for now
            title = iteminfo.get('title').replace('\n', ' ').replace('  ', ' ')

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'en' : title,
                                  }

            if iteminfo.get('media').get('producer'):
                creatorname = iteminfo.get('media').get('producer')

                metadata['creatorname'] = creatorname
                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }

            if iteminfo.get('data').get('Date'):
                if len(iteminfo.get('data').get('Date'))==4 and iteminfo.get('data').get('Date').isnumeric():
                    # Only match on years for now
                    metadata['inception'] = int(iteminfo.get('data').get('Date'))

            if iteminfo.get('media').get('copyright')=='' and len(iteminfo.get('media').get('images'))>0:
                recentinception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recentinception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recentinception = True
                if not recentinception:
                    metadata['imageurl'] = iteminfo.get('media').get('images')[0].get('downloadUrl')
                    metadata['imageurlformat'] = 'Q2195' #JPEG
                    metadata['imageurllicense'] = 'Q20007257' # cc-by-sa.40
                    metadata['imageoperatedby'] = 'Q1132918'
                    #Used this to add suggestions everywhere
                    metadata['imageurlforce'] = True

            yield metadata


def main(*args):
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        if arg.startswith('-create'):
            create = True

    dictGen = getNasjonalmuseetGenerator()

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
