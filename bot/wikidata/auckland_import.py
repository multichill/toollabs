#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Auckland Art Gallery to Wikidata. They seem to provide json:

http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType[0]=Painting&reference=artworks&page=2

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.


"""
import artdatabot
import pywikibot
import requests
import re
import time

def getAucklandArtGenerator():
    """
    Generator to return Auckland Art Gallery paintings

    """

    basesearchurl = u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType[0]=Painting&reference=artworks&page=%s'
    origin = u'"http://www.aucklandartgallery.com'
    referer = u'http://www.aucklandartgallery.com/search/artworks?section=collection&undated=undated&objectType%5B0%5D=Painting'

    # Just loop over the pages
    for i in range(1, 187):
        print i
        searchurl = basesearchurl % (i,)
        searchPage = requests.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                      'referer' : referer,
                                                      'origin' : origin} )

        # This might bork evey once in a while, we'll see
        try:
            searchJson = searchPage.json()
        except ValueError:
            print u'Oh, noes, no JSON. Wait and try again'
            time.sleep(15)
            searchPage = requests.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                          'referer' : referer,
                                                          'origin' : origin} )
            searchJson = searchPage.json()

        for record in searchJson.get('data'):
            metadata = {}
            url =  u'http://www.aucklandartgallery.com/explore-art-and-ideas/artwork/%s/%s' % (record.get('id'),
                                                                                               record.get('slug'),)

            print url
            metadata['url'] = url

            metadata['collectionqid'] = u'Q4819492'
            metadata['collectionshort'] = u'Auckland'

            # This will only work when it's a year
            if record.get('accession_date_earliest') and \
                record.get('accession_date_latest') and \
                record.get('accession_date_earliest')[0:4]==record.get('accession_date_latest')[0:4]:
                    metadata['acquisitiondate'] = record.get('accession_date_earliest')[0:4]

            elif record.get('accession_date'):
                metadata['acquisitiondate'] = record.get('accession_date')

            metadata['locationqid'] = u'Q4819492'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record[u'accession_no']
            metadata['idpid'] = u'P217'


            if type(record.get('name')) is list:
                title = record.get('name')[0]
            else:
                title = record.get('name')


            # Chop chop, several very long titles
            if title > 220:
                title = title[0:200]

            metadata['title'] = { u'en' : title,
                                }

            metadata['creatorname'] = record.get('artists')[0].get('display_name')

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }
            metadata['medium'] = record.get('material_desc')
            metadata['inception'] = record.get('prod_pri_date')


            if record.get('dimensions'):
                regex_2d = u'(?P<height>\d+) x (?P<width>\d+) mm'
                regex_3d = u'(?P<height>\d+) x (?P<width>\d+) x (?P<depth>\d+) mm'
                match_2d = re.match(regex_2d, record.get('dimensions'))
                match_3d = re.match(regex_3d, record.get('dimensions'))
                if match_2d:
                    metadata['heightcm'] = unicode(float(match_2d.group(u'height'))/10)
                    metadata['widthcm'] = unicode(float(match_2d.group(u'width'))/10)
                elif match_3d:
                    metadata['heightcm'] = unicode(float(match_3d.group(u'height'))/10)
                    metadata['widthcm'] = unicode(float(match_3d.group(u'width'))/10)
                    metadata['depthcm'] = unicode(float(match_3d.group(u'depth'))/10)

            if record.get('has_copyright')==False and record.get('images'):
                metadata[u'imageurl'] = record.get('images').get(u'files')[0].get(u'zoom')
                metadata[u'imageurlformat'] = u'Q2195' #JPEG

            yield metadata

    return
    
def main():
    dictGen = getAucklandArtGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
