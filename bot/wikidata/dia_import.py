#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Detroit Institute of Arts to Wikidata.

Just loop over pages like https://www.dia.org/art/collection?&classification%5B0%5D=11507&sort_bef_combine=field_tms_date_year_from%20ASC&Submit_Collection_Search=Search%20Collection&page=10

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getDIAGenerator():
    """
    Generator to return Detroit Institute of Arts paintings
    """
    basesearchurl = u'https://www.dia.org/art/collection?&classification%%5B0%%5D=11507&sort_bef_combine=field_tms_date_year_from%%20ASC&Submit_Collection_Search=Search%%20Collection&page=%s'
    htmlparser = HTMLParser()

    # To not trip this nonsense https://www.sucuri.net/
    headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0' }

    session = requests.Session()
    session.headers.update(headers)

    for i in range(0, 347):
        searchurl = basesearchurl % (i,)

        time.sleep(2)
        print (searchurl)
        searchPage = session.get(searchurl)

        # Grab basic info from item: Artist, url, title and maybe date

        itemregex = u'\<div class\=\"data\"\>[\r\n\t\s]*\<div class\=\"artist\"\>(?P<artist>[^\<]+)\<\/div\>[\r\n\t\s]*\<h3\>\<a href\=\"\/art\/collection\/object\/(?P<url>[^\"]+)\"\>(?P<title>[^\<]+)\<\/a\>\<\/h3\>[\r\n\t\s]*\<div class\=\"date\"\>(?P<date>[^\<]*)\<\/div\>[\r\n\t\s]*\<\/div\>'

        matches = re.finditer(itemregex, searchPage.text)
        for match in matches:
            url = u'https://www.dia.org/art/collection/object/%s' % (match.group(u'url'),)
            metadata = {}

            print (url)

            metadata['url'] = url

            metadata['collectionqid'] = u'Q1201549'
            metadata['collectionshort'] = u'DIA'
            metadata['locationqid'] = u'Q1201549'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # First process the basic info

            title = htmlparser.unescape(match.group(u'title')).strip()

            ## Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }
            name = htmlparser.unescape(match.group(u'artist')).strip()

            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                        u'en' : u'painting by %s' % (name, ),
                                        u'de' : u'Gemälde von %s' % (name, ),
                                        }

            # Work on the previous extracted date
            if match.group(u'date'):
                dateregex = u'(\d\d\d\d)'
                datecircaregex = u'ca?\.\s*(\d\d\d\d)'
                periodregex = u'between\s*(\d\d\d\d)\s*and\s*(\d\d\d\d)|(\d\d\d\d)-(\d\d\d\d)|(\d\d\d\d)/(\d\d\d\d)'
                #shortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>(\d\d)(\d\d)–(\d\d)\<\/p\>'
                circaperiodregex = u'ca\.\s*between\s*(\d\d\d\d)\s*and\s*(\d\d\d\d)'
                #circashortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d)(\d\d)–(\d\d)\<\/p\>'
                datematch = re.search(dateregex, match.group(u'date'))
                datecircamatch = re.search(datecircaregex, match.group(u'date'))
                periodmatch = re.search(periodregex, match.group(u'date'))
                #shortperiodmatch = re.search(shortperiodregex, itempage.text)
                circaperiodmatch = re.search(circaperiodregex, match.group(u'date'))
                #circashortperiodmatch = re.search(circashortperiodregex, itempage.text)
                if datematch:
                    metadata['inception'] = datematch.group(1).strip()
                elif datecircamatch:
                    metadata['inception'] = datecircamatch.group(1).strip()
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1))
                    metadata['inceptionend'] = int(periodmatch.group(2))
                #elif shortperiodmatch:
                #    metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                #    metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                    metadata['inceptionend'] = int(circaperiodmatch.group(2))
                    metadata['inceptioncirca'] = True
                #elif circashortperiodmatch:
                #    metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                #    metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                #    metadata['inceptioncirca'] = True
                else:
                    print (u'Could not parse date: "%s"' % (match.group(u'date'),))

            # Now get the page to get other data
            time.sleep(2)
            itempage = session.get(url)

            metadata['idpid'] = u'P217'

            invregex = u'\<th\>Accession Number\<\/th\>[\r\n\t\s]*\<td\>([^\<]+)\<\/td\>'
            invmatch = re.search(invregex, itempage.text)
            metadata['id'] = invmatch.group(1).strip()

            # No data, could do a trick with the inventory number. Provenance looks messy
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            mediumregex = u'\<th\>Medium\<\/th\>[\r\n\t\s]*\<td\>oil on canvas\<\/td\>'

            mediumematch = re.search(mediumregex, itempage.text)
            if mediumematch:
                metadata['medium'] = u'oil on canvas'

            """
            # Framed, unframed, .....
            measurementsregex = u'\<dt\>\<h3 class\=\"object__accordion-title\"\>Dimensions\<\/h3\>\<\/dt\>[\r\n\t\s]*\<dd\>[\r\n\t\s]*\<div\>[\r\n\t\s]*\<div class\=\"field field--name-field-dimensions field--type-string field--label-hidden\"\>([^\<]+)\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'^(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm.*'
                regex_3d = u'^(?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')
            """
            imageurlregex = u'\<div class\=\"qtip-container icon-download\" data-content\=\"Download this Image\"\>\<a href\=\"(https\:\/\/www\.dia\.org\/sites\/default\/files\/tms-collections-objects\/[^\"]+\.jpg)\"\>\<span  class\=\"fa-2x fa-stack\" aria-label\=\"Download this Image\"\>'
            imageurlmatch = re.search(imageurlregex, itempage.text)

            if imageurlmatch:
                metadata[u'imageurl'] = imageurlmatch.group(1)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                # metadata[u'imageurllicense'] = u'' no explicit license
                # Could use this later to force
                metadata[u'imageurlforce'] = True

            yield metadata


def main():
    dictGen = getDIAGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
