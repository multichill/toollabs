#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Indianapolis Museum of Art to Wikidata.

Old school screen scraping? NO, I found JSON :-)

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.


"""
import artdatabot
import pywikibot
import requests

def getIMAGenerator():
    """
    Generator to return Indianapolis Museum of Art paintings

    Loop over the two base urls, generate a list of search urls. Process that

    """
    searchurls = []
    #
    # paintings 0 - 61
    for i in range(0, 61):
        searchurls.append(u'http://dagwood.imalab.us/api/v1/search/?&query=&type=paintings&page=%s' % (i,))
    # oil paintings 0 - 120
    for i in range(0, 120):
        searchurls.append(u'http://dagwood.imalab.us/api/v1/search/?&query=&type=oil paintings&page=%s' % (i,))

    # Just loop over the pages
    for searchurl in searchurls:
        print searchurl
        searchPage = requests.get(searchurl)
        searchJson = searchPage.json()

        for resultdata in searchJson.get('results'):
            record = resultdata.get('source')

            metadata = {}
            url =  record.get('url')

            print url
            metadata['url'] = url

            metadata['collectionqid'] = u'Q1117704'
            metadata['collectionshort'] = u'IMA'

            # This will only work when it's a year
            if record.get('metadata').get('accession_date_calc'):
                metadata['acquisitiondate'] = record.get('metadata').get('accession_date_calc')[0:4]

            metadata['locationqid'] = u'Q1117704'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Get the ID. This needs to burn if it's not available
            metadata['id'] = record.get('metadata')[u'accession_num']
            metadata['idpid'] = u'P217'

            metadata['artworkidpid'] = u'P4674'
            metadata['artworkid'] = u'%s' % (record.get(u'object_id'),)

            title = record.get('metadata')[u'title']

            # Chop chop, several very long titles
            if title > 220:
                title = title[0:200]

            metadata['title'] = { u'en' : title,
                                }

            if record.get('metadata').get('actors'):
                name = record.get('metadata').get('actors')[0].get('filter_name')
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)
                metadata['creatorname'] = name

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'

            metadata['medium'] = record.get('metadata').get('medium_support')

            # Different ways to get the right date
            if record.get('metadata').get('date_created') == record.get('metadata').get('date_earliest') and \
                            record.get('metadata').get('date_created') == record.get('metadata').get('date_latest'):
                metadata['inception'] = record.get('metadata').get('date_created')
            elif record.get('metadata').get('date_created') and record.get('metadata').get('date_earliest') == None and \
                    record.get('metadata').get('date_latest') == None:
                metadata['inception'] = record.get('metadata').get('date_created')
            elif record.get('metadata').get('date_earliest') and \
                            record.get('metadata').get('date_earliest') == record.get('metadata').get('date_latest'):
                metadata['inception'] = record.get('metadata').get('date_earliest')

            # Find an image we can download
            if record.get('metadata').get(u'can_download') and record.get(u'has_image'):
                if record.get('metadata').get(u'rights') and record.get('metadata').get(u'rights')[0]==u'Public Domain':
                    for image in record.get(u'images'):
                        if image.get(u'image_type')==u'original':
                            metadata[u'imageurl'] = image.get(u'url')
                            metadata[u'imageurlformat'] = u'Q2195' #JPEG
                            # Only one image
                            break

            # Scary inches!
            #if record.get('dimensions'):
            #    regex_2d = u'(?P<height>\d+) x (?P<width>\d+) mm'
            #    regex_3d = u'(?P<height>\d+) x (?P<width>\d+) x (?P<depth>\d+) mm'
            #    match_2d = re.match(regex_2d, record.get('dimensions'))
            #    match_3d = re.match(regex_3d, record.get('dimensions'))
            #    if match_2d:
            #        metadata['heightcm'] = unicode(float(match_2d.group(u'height'))/10)
            #        metadata['widthcm'] = unicode(float(match_2d.group(u'width'))/10)
            #    elif match_3d:
            #        metadata['heightcm'] = unicode(float(match_3d.group(u'height'))/10)
            #        metadata['widthcm'] = unicode(float(match_3d.group(u'width'))/10)
            #        metadata['depthcm'] = unicode(float(match_3d.group(u'depth'))/10)

            yield metadata

    return
    
def main():
    dictGen = getIMAGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=False)
    artDataBot.run()

if __name__ == "__main__":
    main()
