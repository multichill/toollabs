#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintngs from São Paulo Museum of Art.

* Loop over https://masp.org.br/acervo/busca?author=&category=Pintura#collections
* Grab individual paintings like https://masp.org.br/acervo/obra/o-escolar-o-filho-do-carteiro-gamin-au-kepi-o-filho-do-carteiro-gamin-au-kepi

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

def getMASPGenerator():
    """
    Generator to return Yale paintings
    
    """
    htmlparser = HTMLParser()

    searchUrl = u'https://masp.org.br/acervo/busca?author=&category=Pintura#collections'
    searchPage = requests.get(searchUrl)
    searchPageData = searchPage.text
    searchRegex = u'\<a href\=\"(https\:\/\/masp\.org\.br\/acervo\/obra\/[^\"]+)\"\>'

    for match in re.finditer(searchRegex, searchPageData):
        url = match.group(1)
        print (url)
        metadata = {}

        metadata['collectionqid'] = u'Q82941'
        metadata['collectionshort'] = u'MASP'
        metadata['locationqid'] = u'Q82941'

        # Search is for paintings
        metadata['instanceofqid'] = u'Q3305213'
            
        metadata['url'] = url

        itemPage = requests.get(url)
        itemPageData = itemPage.text

        titleRegex = u'\<li\>\<h5 class\=\"sub-title slim inline-block\"\>Título\:\<\/h5\>([^\<]+)\<\/li\>'
            
        matchTitle = re.search(titleRegex, itemPageData)

        metadata['title'] = { u'pt' : htmlparser.unescape(matchTitle.group(1).strip(u'\s\r\n\t')),
                            }
        creatorRegex = u'\<li\>\<h5 class\=\"sub-title slim inline-block\"\>Autor\:\<\/h5\>([^\<]+)\<\/li\>'

        creatorMatch = re.search(creatorRegex, itemPageData)

        metadata['creatorname'] = creatorMatch.group(1)

        metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                    u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                    u'pt' : u'%s de %s' % (u'pintura', metadata.get('creatorname'),),
                                    }

        invRegex = u'\<li\>\<h5 class\=\"sub-title slim inline-block\"\>Número de inventário\:\<\/h5\>([^\<]+)\<\/li\>'
        invMatch = re.search(invRegex, itemPageData)

        metadata['idpid'] = u'P217'
        metadata['id'] = invMatch.group(1)

        dateRegex = u'\<li\>\<h5 class\=\"sub-title slim inline-block\"\>Data da obra\:\<\/h5\>(\d\d\d\d)\<\/li\>'
        dateMatch = re.search(dateRegex, itemPageData)
        if dateMatch:
            metadata['inception'] = dateMatch.group(1)

        acquisitiondateRegex = u'\<li\>\<h5 class\=\"sub-title slim inline-block\"\>Aquisição\:\<\/h5\>[^\<]+(\d\d\d\d)\<\/li\>'
        acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
        if acquisitiondateMatch:
            metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

        mediumRegex = u'\<li\>\<h5 class\=\"sub-title slim inline-block\"\>Técnica\:\<\/h5\>([^\<]+)\<\/li\>'
        mediumMatch = re.search(mediumRegex, itemPageData)

        if mediumMatch and mediumMatch.group(1).strip().lower()==u'Óleo sobre tela'.lower():
            metadata['medium'] = u'oil on canvas'

        dimensionRegex = u'\<li\>\<h5 class\=\"sub-title slim inline-block\"\>Dimensões\:\<\/h5\>([^\<]+)\<\/li\>'
        dimensionMatch = re.search(dimensionRegex, itemPageData)

        if dimensionMatch:
            dimensiontext = dimensionMatch.group(1).strip()

            # 73x59.5x0.5 cm
            #regex_2d = u'unframed\:\s*(?P<height>\d+(\.\d+)?)\s*(x|x|×)\s*(?P<width>\d+(\.\d+)?)\s*cm.*'
            regex_3d = u'(?P<height>\d+(\.\d+)?)\s*(x|×)\s*(?P<width>\d+(\.\d+)?)\s*(x|×)\s*(?P<depth>\d+(\.\d+)?)\s*cm'
            #match_2d = re.match(regex_2d, dimensiontext)
            match_3d = re.match(regex_3d, dimensiontext)
            #if match_2d:
            #    metadata['heightcm'] = match_2d.group(u'height')
            #    metadata['widthcm'] = match_2d.group(u'width')
            if match_3d:
                metadata['heightcm'] = match_3d.group(u'height')
                metadata['widthcm'] = match_3d.group(u'width')
                metadata['depthcm'] = match_3d.group(u'depth')
        # Image use policy unclear
        #imageregex = u'\<div class\=\"photo-copyright\"\>\<a href\=\"\/node\/268102\"\>Public domain\<\/a\>\<\/div\>\<div class\=\"photo-download\"\>\<a class\=\"download\" href\=\"(http\:\/\/deliver\.odai\.yale\.edu\/content\/id\/[^\/]+\/format\/3)\"\>Download presentation-size image'
        #imageMatch = re.search(imageregex, itemPageData)

        #if imageMatch:
        #    metadata[u'imageurl'] = imageMatch.group(1)
        #    metadata[u'imageurlformat'] = u'Q2195' #JPEG

        yield metadata


def main():
    dictGen = getMASPGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
