#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from National Museum of Art, Architecture and Design

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import json
import re

def getNasjonalmuseetGenerator():
    """
    Generator to return Nasjonalmuseet paintings
    """
    baseSearchUrl = u'http://samling.nasjonalmuseet.no/en/term/name/Maleri?lang=en&action=search&fq=artifact.name:Maleri&start=%s'

    for i in range(2336, 4753, 12):
        searchurl = baseSearchUrl % (i,)
        pywikibot.output (searchurl)
        searchPage = requests.get(searchurl)

        searchRegex = u'href\=\"\/en\/object\/([^\"]+)\"\>'
        matches = re.finditer(searchRegex, searchPage.text)
        for match in matches:
            # Norway doesn't seem to have discovered SSL yet.
            url = u'http://samling.nasjonalmuseet.no/en/object/%s' % match.group(1)

            pywikibot.output (url)

            metadata = {}
            metadata['url'] = url

            metadata['collectionqid'] = u'Q1132918'
            metadata['collectionshort'] = u'Nasjonalmuseet'
            metadata['locationqid'] = u'Q1132918'

            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'

            itempage = requests.get(url)
            metadataregex = u'td class\=\"term\"\>Metadata\:\<\/td\>\<td class\=\"value\"\>\<a href\=\"(http\:\/\/api\.dimu\.org\/artifact\/uuid\/[^\"]+)\"'

            metadataurl = re.search(metadataregex, itempage.text).group(1)

            print metadataurl

            metadatapage = requests.get(metadataurl)
            #metadatapage.encoding = u'utf-8'
            item = metadatapage.json()
            #print (item)

            # TODO: Check multiple titles
            if item.get(u'titles'):
                title = None
                if item.get(u'titles')[0].get(u'title'):
                    title = item.get(u'titles')[0].get(u'title')
                elif item.get(u'titles')[1].get(u'title'):
                    title = item.get(u'titles')[1].get(u'title')

                if title:
                    if len(title) > 220:
                        title = title[0:200]
                    metadata['title'] = { u'no' : title,
                                          }
                else:
                    metadata['title'] = {}
            else:
                metadata['title'] = {}

            ## I had one item with missing identifier, wonder if it shows up here too
            metadata['idpid'] = u'P217'
            #if not item.get('identifier'):
            #    # Few rare items without an inventory number, just skip them
            #    continue
            metadata['id'] = item.get('identifier').get(u'id')

            if item.get('eventWrap').get(u'producers'):
                name = item.get('eventWrap').get(u'producers')[0].get(u'name')
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)
                metadata['creatorname'] = name

                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
            else:
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous paintiner',
                                            }
                metadata['creatorqid'] = u'Q4233718'

            #if item.get('authority_id') and item.get('authority_id')[0]:
            #    artistid = item.get('authority_id')[0]
            #    if artistid in webumeniaArtists:
            #        pywikibot.output (u'Found Webumenia id %s on %s' % (artistid, webumeniaArtists.get(artistid)))
            #        metadata['creatorqid'] = webumeniaArtists.get(artistid)

            if item.get('eventWrap').get(u'production').get(u'timespan') and \
                    item.get('eventWrap').get(u'production').get(u'timespan').get(u'fromYear') and \
                    item.get('eventWrap').get(u'production').get(u'timespan').get(u'fromYear')==item.get('eventWrap').get(u'production').get(u'timespan').get(u'toYear'):
                metadata['inception'] = item.get('eventWrap').get(u'production').get(u'timespan').get(u'fromYear')


            if item.get('eventWrap').get(u'acquisition'):
                acquisitiondateRegex = u'^.+(\d\d\d\d)$'
                acquisitiondateMatch = re.match(acquisitiondateRegex, item.get('eventWrap').get(u'acquisition'))
                if acquisitiondateMatch:
                    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            if item.get(u'material') and item.get(u'material').get(u'comment') and item.get(u'material').get(u'comment')==u'Olje på lerret':
                metadata['medium'] = u'oil on canvas'

            # measurement
            if item.get(u'measures'):
                for measure in item.get(u'measures'):
                    if measure.get(u'unit')==u'cm':
                        if measure.get(u'category') and (measure.get(u'category')==u'Rammemål' or not measure.get(u'category')==u'Hovedmål'):
                            # We found something else than the painting size
                            continue
                        if measure.get(u'type')==u'Høyde':
                            metadata['heightcm'] = u'%s' % (measure.get(u'measure'),)
                        elif measure.get(u'type')==u'Bredde':
                            metadata['widthcm'] = u'%s' % (measure.get(u'measure'),)
                        elif measure.get(u'type')==u'Dybde':
                            metadata['depthcm'] = u'%s' % (measure.get(u'measure'),)

            # Imageurl could easily be constructed here, but content is not free :-(
            #if item.get(u'has_image') and item.get(u'is_free') and item.get(u'has_iip'):
            #    metadata[u'imageurl'] = u'https://www.webumenia.sk/dielo/%s/stiahnut' % (item.get('id'),)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
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
