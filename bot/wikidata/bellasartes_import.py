#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Museo Nacional de Bellas Artes in Buenos Aires to Wikidata.

Start at http://www.bellasartes.gob.ar/coleccion/objeto/pintura and use a session to retrieve the rest.

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getBellasartesGenerator():
    """
    Generator to return Museo Nacional de Bellas Artes paintings
    """
    firsturl = u'http://www.bellasartes.gob.ar/coleccion/objeto/pintura'
    ajaxurl = u'http://www.bellasartes.gob.ar/coleccion/resultados/ajax'

    invnums = []

    s = requests.Session()
    firstPage = s.get(firsturl)
    urlregex = u'\<a href\=\"\/coleccion\/obra\/(\d+)\" title\='
    matches = re.finditer(urlregex, firstPage.text)
    for match in matches:
        invnums.append(match.group(1))

    getmoredata = True
    while getmoredata:
        searchPage = s.post(ajaxurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                      'referer' : firsturl,
                                                     } )
        searchjson =  searchPage.json()
        for object in searchjson.get('data'):
            invnums.append(object.get('numInv'))
        if not searchjson.get('data'):
            getmoredata = False

    htmlparser = HTMLParser.HTMLParser()

    for invnum in invnums:
        metadata = {}
        url =  u'http://www.bellasartes.gob.ar/coleccion/obra/%s' % (invnum,)
        print url

        itempage = s.get(url)
        metadata['url'] = url

        metadata['collectionqid'] = u'Q1848918'
        metadata['collectionshort'] = u'Bellas Artes'
        metadata['locationqid'] = u'Q1848918'

        #No need to check, I'm actually searching for paintings.
        metadata['instanceofqid'] = u'Q3305213'

        metadata['id'] = invnum
        metadata['idpid'] = u'P217'

        titleregex = u'\<div id\=\"data\"\>\s*\n*\s*\<h1\>([^\<]+)\<\/h1\>'
        titlematch = re.search(titleregex, itempage.text)
        if not titlematch:
            pywikibot.output(u'No title match, something went wrong on %s' % (url,))
            continue
        ## Chop chop, several very long titles
        #if title > 220:
        #    title = title[0:200]
        metadata['title'] = { u'es' : htmlparser.unescape(titlematch.group(1).strip()),
                              }

        creatorregex = u'\<li  class\=\"autor\"\>\s*\n*\s*Autor\:s*\n*\s*\<span\>\<strong\>([^\<]+)\<\/strong\>'
        creatormatch = re.search(creatorregex, itempage.text)
        name = htmlparser.unescape(creatormatch.group(1).strip())
        if u',' in name:
            (surname, sep, firstname) = name.partition(u',')
            name = u'%s %s' % (firstname.strip(), surname.strip(),)
        if name==u'Anónimo':
            metadata['creatorname'] = u'anonymous'
            metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                        u'en' : u'painting by anonymous painter',
                                        u'es' : u'cuadro de autor desconocido',
                                        }
            metadata['creatorqid'] = u'Q4233718'
        else:
            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', name,),
                                        u'en' : u'%s by %s' % (u'painting', name,),
                                        u'es' : u'%s de %s' % (u'cuadro', name,),
                                        }

        acquisitiondateregex = u'\<li\>Origen\: \<span\>[^\<]+(\d\d\d\d)\<\/span\>'
        acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
        if acquisitiondatematch:
            metadata['acquisitiondate'] = acquisitiondatematch.group(1)

        inceptionregex = u'\<li\>Fecha\: \<span\>(\d\d\d\d)\<\/span\>'
        inceptionmatch = re.search(inceptionregex, itempage.text)
        if inceptionmatch:
            metadata['inception'] = inceptionmatch.group(1)

        # Only add the medium if it's oil on canvas
        oilregex = u'Técnica\:\s*\n*\s*\<span\><a href\=\"\/coleccion\/tecnica\/leo\" title\=\"Óleo\"\>Óleo\<\/a\>\<\/span\>'
        canvasregex = u'\<li\>Soporte\: \<span\>sobre tela\<\/span\>\<\/li\>'
        oilmatch = re.search(oilregex, itempage.text)
        canvasmatch = re.search(canvasregex, itempage.text)
        if oilmatch and canvasmatch:
            metadata['medium'] = u'oil on canvas'

        medidasregex = u'\<li\>Medidas\: \<span\>([^\<]+)\<\/span\>'
        medidasmatch = canvasmatch = re.search(medidasregex, itempage.text)
        if medidasmatch:
            medidastext = medidasmatch.group(1)
            regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm.*'
            regex_3d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm.*'
            match_2d = re.match(regex_2d, medidastext)
            match_3d = re.match(regex_3d, medidastext)
            if match_2d:
                metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
            elif match_3d:
                metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

        yield metadata


def main():
    dictGen = getBellasartesGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
