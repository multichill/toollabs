#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from Yale University Art Gallery.

* Loop over https://artgallery.yale.edu/collection/search?f%5B0%5D=field_facet_classification%3A99
* Grab individual paintings like https://artgallery.yale.edu/collections/objects/149203

Use artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getYaleGenerator():
    """
    Generator to return Yale paintings
    
    """

    # 1 - 22
    #searchBaseUrl = u'http://collections.britishart.yale.edu/vufind/Search/Results?join=AND&bool0[]=AND&lookfor0[]=%%22Paintings+and+Sculpture%%22&type0[]=collection&bool1[]=AND&lookfor1[]=Painting&type1[]=type_facet&page=%s&view=grid'
    searchBaseUrl = u'https://artgallery.yale.edu/collection/search?page=%s&f%%5B0%%5D=field_facet_classification%%3A99&sort=search_api_aggregation_2&order=asc'
    htmlparser = HTMLParser()

    session = requests.Session()

    #foundit=True
    # O tot 572
    for i in range(0, 572):
        searchUrl = searchBaseUrl % (i,)
        print (searchUrl)
        searchPage = session.get(searchUrl)
        searchPageData = searchPage.text

        searchRegex = u'property\=\"dc\:title\"\>\<h2\>\<a href\=\"\/collections\/objects\/(\d+)\"\>'

        for match in re.finditer(searchRegex, searchPageData):
            url = u'https://artgallery.yale.edu/collections/objects/%s' % (match.group(1),)
            print (url)
            metadata = {}

            metadata['collectionqid'] = u'Q1568434'
            metadata['collectionshort'] = u'Yale'
            metadata['locationqid'] = u'Q1568434'
            # Search is for paintings
            metadata['instanceofqid'] = u'Q3305213'
            
            metadata['url'] = url

            itemPage = requests.get(url) #, verify=False)
            itemPageData = itemPage.text # unicode(itemPage.read(), u'utf-8')

            #yield metadata

            #print itemPageEnData
            #titleRegex = u'<th id\="titleHeaders">Title\s*</th>[\r\n\t\s]+<td id="dataField">[\r\n\t\s]+([^<]+)[\r\n\t\s]+</td>'
            #titleRegex = u'property\=\"dc\:title\"\>\<h1\>[\r\n\t\s]*([^<]+)[\r\n\t\s]*\<\/h1\>'
            titleRegex = u'\<title\>[\r\n\t\s]*([^<]+)[\r\n\t\s]*\| Yale University Art\xa0Gallery\<\/title\>'
            
            matchTitle = re.search(titleRegex, itemPageData)
            if not matchTitle:
                pywikibot.output(u'The title data for this painting is BORKED!')
                return

            metadata['title'] = { u'en' : htmlparser.unescape(matchTitle.group(1).strip(u'\s\r\n\t').strip()),
                                  }
            #pywikibot.output(metadata.get('title'))

            creatorRegex = u'\"field field-name-object-artists field-type-ds field-label-hidden\"\>[\r\n\t\s]+\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>\<div class\=\"field\"\>\<span class\=\"field-label\"\>Artist( attributed)?\<\/span\>\:[\r\n\t\s]*(?P<creator>[^,\<]+)[^\<]*\<'

            creatorMatch = re.search(creatorRegex, itemPageData)
            if creatorMatch:
                metadata['creatorname'] = creatorMatch.group(u'creator')

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'

            #invRegex = u'<th id=\"titleHeaders\">Accession Number[\r\n\t\s]+</th>[\r\n\t\s]+<td id=\"dataField\">[\r\n\t\s]+<span title="Object ID:[\r\n\t\s]+(\d+)">[\r\n\t\s]+([^\r\n\t\s]+)[\r\n\t\s]+</span>[\r\n\t\s]+</td>'
            invRegex = u'\"field field-name-field-object-number field-type-text field-label-hidden\"\>[\r\n\t\s]+\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>[\r\n\t\s]*([^\<]+)\<\/div\>'
            invMatch = re.search(invRegex, itemPageData)

            if invMatch:
                metadata['id'] = invMatch.group(1)
            else:
                invRegex = u'\"field field-name-field-object-number field-type-text field-label-hidden\"\>[\r\n\t\s]+\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>\<span class=\"caps\"\>([^\<]+)\<\/span\>([^\<]+)\<\/div\>'
                invMatch = re.search(invRegex, itemPageData)
                if not invMatch:
                    pywikibot.output(u'No inventory number found! Skipping')
                    continue # Return
                else:
                    metadata['id'] = u'%s%s' % (invMatch.group(1), invMatch.group(2))


            metadata['idpid'] = u'P217'

            dateRegex = u'\"field field-name-field-dated field-type-text field-label-hidden\"\>[\r\n\t\s]+\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>(\d\d\d\d)\<\/div\>'
            circaperiodregex = u'\"field field-name-field-dated field-type-text field-label-hidden\"\>[\r\n\t\s]+\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>ca\.\s*(\d\d\d\d)–(\d\d\d\d)\<\/div\>'
            circaregex = u'\"field field-name-field-dated field-type-text field-label-hidden\"\>[\r\n\t\s]+\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>ca\.\s*(\d\d\d\d)\<\/div\>'

            datematch = re.search(dateRegex, itemPageData)
            circaperiodmatch = re.search(circaperiodregex, itemPageData)
            circamatch = re.search(circaregex, itemPageData)

            if datematch:
                metadata['inception'] = datematch.group(1)
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                metadata['inceptioncirca'] = True
            elif circamatch:
                metadata['inception'] = circamatch.group(1)
                metadata['inceptioncirca'] = True

            # Data not available
            # record.get('acquisition')

            mediumRegex = u'\"field field-name-field-medium field-type-text-long field-label-hidden\"\>[\r\n\t\s]*\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>\<p\>[\r\n\t\s]*([^\<]+)[\r\n\t\s]*\<\/p\>\<\/div\>'
            mediumMatch = re.search(mediumRegex, itemPageData)

            if mediumMatch and mediumMatch.group(1).strip().lower()==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'

            dimensionRegex = u'\"field field-name-field-dimensions field-type-text field-label-hidden\"\>[\r\n\t\s]*\<div class\=\"field-items\"\>[\r\n\t\s]*\<div class\=\"field-item even\"\>([^\<]+)\<'
            dimensionMatch = re.search(dimensionRegex, itemPageData)

            if dimensionMatch:
                dimensiontext = dimensionMatch.group(1).strip()

                regex_2d = u'unframed\:\s*(?P<height>\d+(\.\d+)?)\s*(x|x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm.*'
                #regex_3d = u'.*\((?P<height>\d+(\.\d+)?) (x|×) (?P<width>\d+(\.\d+)?) (x|×) (?P<depth>\d+(\.\d+)?) cm\)'
                match_2d = re.match(regex_2d, dimensiontext, flags=re.DOTALL)
                #match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                #elif match_3d:
                #    metadata['heightcm'] = match_3d.group(u'height')
                #    metadata['widthcm'] = match_3d.group(u'width')
                #    metadata['depthcm'] = match_3d.group(u'depth')

            imageregex = u'\<div class\=\"photo-copyright\"\>\<a href\=\"\/node\/268102\"\>Public domain\<\/a\>\<\/div\>\<div class\=\"photo-download\"\>\<a class\=\"download\" href\=\"(http\:\/\/deliver\.odai\.yale\.edu\/content\/id\/[^\/]+\/format\/3)\"\>Download presentation-size image'
            imageMatch = re.search(imageregex, itemPageData)

            if imageMatch:
                metadata[u'imageurl'] = imageMatch.group(1)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG

            yield metadata

def main():
    dictGen = getYaleGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
