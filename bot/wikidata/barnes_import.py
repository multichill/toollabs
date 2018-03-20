#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Barnes Foundation (Q808462) to Wikidata.

Just loop over all results at https://collection.barnesfoundation.org/api/search?body={%22from%22:0}

This bot does use artdatabot to upload it to Wikidata.

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

def getBarnesGenerator():
    """
    Generator to return Barnes Foundation paintings
    """
    size = 100
    basesearchurl = u'https://collection.barnesfoundation.org/api/search?body={%%22from%%22:%s,%%22size%%22:%s}'
    htmlparser = HTMLParser()

    # 963 results, 20 per page (starting at 0)
    for i in range(0, 2700, size):
        searchurl = basesearchurl % (i,size)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)
        searchJson = searchPage.json()

        for object in searchJson.get(u'hits').get(u'hits'):
            item = object.get(u'_source')
            #print (item)
            metadata = {}
            #print (item.get('classification'))
            if not item.get('classification')==u'Paintings':
                continue
            #We checked, it's a painting
            metadata['instanceofqid'] = u'Q3305213'

            #print (itemurl)

            url = u'https://collection.barnesfoundation.org/objects/%s/details' % (item.get('id'),)

            # Museum site probably doesn't like it when we go fast
            # time.sleep(5)

            pywikibot.output(url)

            #itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q808462'
            metadata['collectionshort'] = u'Barnes'
            metadata['locationqid'] = u'Q808462'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = item.get('invno')
            metadata['idpid'] = u'P217'

            metadata['artworkidpid'] = u'P4709'
            metadata['artworkid'] = u'%s' % (item.get('id'),)

            if item.get('title'):
                title = htmlparser.unescape(item.get('title'))
            else:
                title = u'(without title)'
            metadata['title'] = { u'en' : title,
                                  }

            name =  htmlparser.unescape(item.get('people'))
            #if u',' in name:
            #    (surname, sep, firstname) = name.partition(u',')
            #    name = u'%s %s' % (firstname.strip(), surname.strip(),)
            metadata['creatorname'] = name

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            metadata['inception'] = item.get('displayDate')
            if item.get('medium') and item.get('medium').strip()==u'Oil on canvas':
                metadata['medium'] = u'oil on canvas'

            # Could implement this later again
            #if bigmatch.group(u'dimensions'):
            #    dimensiontext = bigmatch.group(u'dimensions').strip()
            #    regex_2d = u'.+\((?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm\)$'
            #    regex_3d = u'.+\((?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm\)$'
            #    match_2d = re.match(regex_2d, dimensiontext)
            #    match_3d = re.match(regex_3d, dimensiontext)
            #    if match_2d:
            #        metadata['heightcm'] = match_2d.group(u'height')
            #        metadata['widthcm'] = match_2d.group(u'width')
            #    elif match_3d:
            #        metadata['heightcm'] = match_3d.group(u'height')
            #        metadata['widthcm'] = match_3d.group(u'width')
            #        metadata['depthcm'] = match_3d.group(u'depth')

            if not item.get('copyright') and item.get('objRightsTypeId')==u'8':
                if item.get('imageOriginalSecret'):
                    metadata[u'imageurl'] = u'http://s3.amazonaws.com/barnes-image-repository/images/%s_%s_o.jpg' % (item.get('id'), item.get('imageOriginalSecret'))
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            yield metadata


def main():
    dictGen = getBarnesGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
