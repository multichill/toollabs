#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to upload the paintings of the Finnish National Gallery

The JSON file is at http://kokoelmat.fng.fi/api/v2support/docs/#/download

"""
import json
import csv
import pywikibot
import re

def getFNGArtistsGenerator(jsonlocation):
    '''
    Generate the artists based on the JSON file you can find at http://kokoelmat.fng.fi/api/v2support/docs/#/download

    Yield the dict items suitable for artdatabot
    '''

    jsonfile = open(jsonlocation, u'r')
    jsondata = json.load(jsonfile)
    for artistMetadata in jsondata.get('descriptionSet'):
        metadata = {}
        #metadata['collectionqid'] = u'Q2983474'
        #metadata['collectionshort'] = u'FNG'
        foundartist = False
        for typefield in artistMetadata.get('type'):
            if typefield.get(u'type')==u'artist':
                foundartist=True
        if foundartist:
            metadata['type'] = u'artist'
            name = None
            if artistMetadata.get('title') and \
                    artistMetadata.get('title')[0] and \
                    artistMetadata.get('title')[0].get('title'):
                name = artistMetadata.get('title')[0].get('title')
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)
            if not name:
                pywikibot.output(u'No name found, skipping')
                continue
            metadata['name'] = name

            for identifierfield in artistMetadata.get('identifier'):
                if identifierfield.get(u'si'):
                    metadata[u'id'] = identifierfield.get(u'si').replace(u'http://kansallisgalleria.fi/E39.Actor_', u'')
                elif identifierfield.get(u'uri'):
                    metadata[u'url'] = identifierfield.get(u'uri')

            if not metadata.get('id'):
                pywikibot.output(u'No id found, skipping')
                continue

            if artistMetadata.get('date'):
                for datefield in artistMetadata.get('date'):
                    if datefield.get('type'):
                        if datefield.get('type')=='birth':
                            if datefield.get('loc'):
                                metadata['birthlocation'] = datefield.get('loc')
                            if datefield.get('value'):
                                metadata['birthdate'] = datefield.get('value')
                        elif datefield.get('type')=='death':
                            if datefield.get('loc'):
                                metadata['deathlocation'] = datefield.get('loc')
                            if datefield.get('value'):
                                metadata['deathdate'] = datefield.get('value')
                    # The funky formats, doesn't seem to work
                    elif datefield.get('birth'):
                        metadata['birthdate'] = datefield.get('birth')
                    elif datefield.get('death'):
                        metadata['deathate'] = datefield.get('death')
                    else:
                        pywikibot.output(u'Not able to parse date field')
                        print datefield

            # Also build a pretty description here
            description = u'artist'

            if metadata.get('birthdate'):
                if metadata.get('deathdate'):
                    description = description + u' (%s – %s)' % (metadata.get('birthdate'),
                                                                 metadata.get('deathdate'),)
                else:
                    description = description + u' (%s)' % (metadata.get('birthdate'),)
            elif metadata.get('deathdate'):
               description = description + u' (%s – %s)' % (u'unknown',
                                                            metadata.get('deathdate'),)

            if metadata.get('birthlocation'):
                description = description + u', place of birth: %s' % (metadata.get('birthlocation'),)
            if metadata.get('deathlocation'):
                description = description + u', place of death: %s' % (metadata.get('deathlocation'),)
            metadata['description'] = description
            yield metadata


def main(*args):
    jsonlocation = u''
    for arg in pywikibot.handle_args(args):
        jsonlocation = arg

    if not jsonlocation:
        pywikibot.output(u'Need to have the location of the fng-data-dc.json')
        return

    artistGen = getFNGArtistsGenerator(jsonlocation)


    #for artist in artistGen:
    #    print artist

    with open('/tmp/fng_artists.tsv', 'wb') as tsvfile:
        fieldnames = [u'Entry ID', # (your alphanumeric identifier; must be unique within the catalog)
                      u'Entry name', # (will also be used for the search in mix'n'match later)
                      u'Entry description', #
                      u'Entry type', # (short string, e.g. "person" or "location"; recommended)
                      u'Entry URL', # if omitted, it will be constructed from the URL pattern and the entry ID. Either a URL pattern or a URL column are required!
                      ]

        writer = csv.DictWriter(tsvfile, fieldnames, dialect='excel-tab')

        #No header!
        #writer.writeheader()

        for artist in artistGen:
            print artist
            artistdict = {u'Entry ID' : artist[u'id'].encode(u'utf-8'),
                          u'Entry name' : artist[u'name'].encode(u'utf-8'),
                          u'Entry description' : artist[u'description'].encode(u'utf-8'),
                          u'Entry type' : u'person'.encode(u'utf-8'),
                          u'Entry URL': artist[u'url'].encode(u'utf-8'),
                          }
            print artist
            writer.writerow(artistdict)

if __name__ == "__main__":
    main()
