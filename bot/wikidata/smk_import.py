#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to scrape paintings from the Statens Museum for Kunst website.

http://www.smk.dk/en/explore-the-art/search-smk/#/category/collections/fq=object_type%3Amaleri&start=12

"""



import HTMLParser
import time
import json
import artdatabot
import pywikibot
import requests

def getPaintingGenerator(query=u''):
    '''

    Doing a two step approach here. Could do one, but would be complicated
    * Loop over http://www.artic.edu/aic/collections/artwork-search/results/painting?filters=object_type_s%3APainting&page=0 - 237 and grab paintings
    * Grab data from paintings
    '''

    start = 200
    end = 7000
    step = 100

    basestarturl = u'http://solr.smk.dk:8080/proxySolrPHP/proxy.php?wt=json&query=facet%3Dfalse%26facet.field%3Dartist_name_ss%26facet.field%3Dartist_natio%26facet.field%3Dobject_production_century_earliest%26facet.field%3Dobject_type%26facet.field%3D%7B!ex%3Dcategory%7Dcategory%26facet.limit%3D-1%26facet.mincount%3D1%26rows%3D' + unicode(step) + u'%26defType%3Dedismax%26json.nl%3Dmap%26q%3D-%28id_s%253A%28*%252F*%29%2520AND%2520category%253Acollections%29%2520-%28id_s%253A%28*verso%29%2520AND%2520category%253Acollections%29%26fq%3D%7B!tag%3Dcategory%7Dcategory%253Acollections%26fq%3Dobject_type%253Amaleri%26qf%3D%2520id%255E20%2520title_dk%255E5%2520title_eng%255E15%2520title_first%255E15%2520artist_name%255E15%2520page_content%255E10%2520page_title%255E15%2520description_note_dk%255E2%2520description_note_en%255E5%2520prod_technique_dk%255E2%2520prod_technique_en%255E5%2520object_type%255E10%26sort%3Dscore%2520desc%26start%3D'
    baseendurl = u'&prev_query=&solrUrl=http%3A%2F%2Fsolr.smk.dk%3A8080%2Fsolr%2Fprod_all_en%2F&language=en'

    htmlparser = HTMLParser.HTMLParser()

    for i in range (start, end, step):
        searchurl = basestarturl + unicode(i) + baseendurl
        print searchurl
        
    
        searchPage = requests.get(searchurl)
        # Page says some weird Windows encoding, but it's actually utf-8
        searchPage.encoding = 'utf-8'
        searchData = searchPage.text
        #print searchData[1:-1]
        searchDataObject = json.loads(searchData[1:-1])
        #print searchDataObject.get('response')
        for item in searchDataObject.get(u'response').get(u'docs'):
            #print item
            #print json.dumps(item, indent=4, sort_keys=True)
            #time.sleep(2)
            metadata = {}
            url = u'http://www.smk.dk/en/explore-the-art/search-smk/#/detail/%s' % (item.get('id'),)
            print (url)
            metadata[u'url'] = url

            metadata[u'collectionqid'] = u'Q671384'
            metadata[u'collectionshort'] = u'SMK'
            metadata[u'locationqid'] = u'Q671384'

            metadata['idpid'] = u'P217'
            metadata[u'id'] = item['id']

            #No need to check, I'm actually searching for paintings. Right?
            metadata['instanceofqid'] = u'Q3305213'

            metadata['title'] = {}

            if item.get('title_dk'):
                metadata[u'title']['da'] = item['title_dk'].strip()
            else:
                metadata[u'title']['da']  = item['title_first'].strip()

            if item.get('title_eng'):
                metadata[u'title']['en'] = item['title_eng'].strip()
            else:
                metadata[u'title']['en'] = item['title_first'].strip()

            metadata[u'creatorname'] = htmlparser.unescape(item.get('artist_name')[0])

            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                        u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                        }

            metadata[u'inception'] = item.get('object_production_date_text_en')
            metadata[u'acquisitiondate'] = item.get('acq_date')
            if item.get('prod_technique_en'):
                metadata[u'medium'] = item.get('prod_technique_en').lower()

            # Dimensions are unclear what it means. With or without frame?

            # On their website copyright status is cc0 or copyrighted. Trying to figure that out here
            if item.get(u'medium_image_url'):
                foundCopyright = False
                isFree = False
                if item.get(u'artist_death_en') and item.get(u'artist_death_en')[0]:
                    if len(item.get(u'artist_death_en')[0]) > 4:
                        deathyear = item.get(u'artist_death_en')[0][0:4]
                    else:
                        deathyear = item.get(u'artist_death_en')[0]
                    if deathyear.isnumeric():
                        foundCopyright = True
                        if int(deathyear) < 1923:
                            isFree = True
                if not foundCopyright and item.get(u'artist_birth_en') and item.get(u'artist_birth_en')[0]:
                    if len(item.get(u'artist_birth_en')[0]) > 4:
                        birthyear = item.get(u'artist_birth_en')[0][0:4]
                    else:
                        birthyear = item.get(u'artist_birth_en')[0]
                    if birthyear.isnumeric():
                        foundCopyright = True
                        if int(birthyear) < 1850:
                            isFree = True

                if not foundCopyright:
                    if len(metadata[u'inception'])==4 and metadata[u'inception'].isnumeric():
                        foundCopyright = True
                        if int(metadata[u'inception']) < 1850:
                            isFree = True

                if not foundCopyright:
                    if int(item.get(u'object_production_century_earliest')) < 19:
                        foundCopyright = True
                        isFree = True

                if foundCopyright and isFree:
                    metadata[u'imageurl'] = item.get(u'medium_image_url')
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    metadata[u'imageurllicense'] = u'Q6938433' # cc-zero

                if not foundCopyright:
                    print u'Unable to determine copyright'
                    print json.dumps(item, indent=4, sort_keys=True)

            yield metadata


def main():
    paintingGen = getPaintingGenerator()

    #for painting in paintingGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(paintingGen, create=True)
    artDataBot.run()
    
    

if __name__ == "__main__":
    main()
