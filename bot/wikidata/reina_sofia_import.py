#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Reina Sofia Musem ( http://www.museoreinasofia.es/en/collection ) to Wikidata.

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser
import time
import json

def getSofiaGenerator():
    """
    Generator to return Reina Sofia Musem paintings
    """
    basesearchurl = u'http://www.museoreinasofia.es/en/buscar?bundle=obra&keyword=&f[100]=&fecha=&items_per_page=15&pasados=1&sort=autor&f[0]=im_field_obra_clasificaciongener%3A4238&f[0]=im_field_obra_clasificaciongener%3A4238&page=0'

    htmlparser = HTMLParser.HTMLParser()

    # Total results 1601, 15 per page
    for i in range(0, 107):
        print u'Working on search page %s' % (i,)
        searchurl = basesearchurl.replace(u'&page=0', u'&page=%s' % (i,))
        searchPage = requests.get(searchurl)

        searchRegex = u'\<h3 class\=\"titulo\"\>\<a href\=\"(\/en\/collection\/artwork\/[^\"]+)\"\>'
        matches = re.finditer(searchRegex, searchPage.text)

        urls = []
        for match in matches:
            urls.append(u'http://www.museoreinasofia.es%s' % (match.group(1),))

        for url in set(urls):
            print url
            metadata = {}

            metadata['collectionqid'] = u'Q460889'
            metadata['collectionshort'] = u'Reina Sofía'
            metadata['locationqid'] = u'Q460889'
            metadata['instanceofqid'] = u'Q3305213'

            metadata['url'] = url
            itempage = requests.get(url)

            titleregex = u'class\=\"language-link active\" xml\:lang\=\"en\" title\=\"([^\"]+)\"\>EN\<\/a\>\<\/li\>'
            otherlangs = [u'es', u'ca', u'eu', u'gl']
            baselangtitleregex = u'class\=\"language-link\" xml\:lang\=\"%s\" title\=\"([^\"]+)\"\>%s\<\/a\>\<\/li\>'
            titlematch = re.search(titleregex, itempage.text)
            metadata['title'] = { u'en' : htmlparser.unescape(titlematch.group(1).strip()),
                                  }
            for lang in otherlangs:
                langtitleregex = baselangtitleregex % (lang, lang.upper(),)
                langtitlematch = re.search(langtitleregex, itempage.text)
                if langtitlematch:
                    metadata['title'][lang] = htmlparser.unescape(langtitlematch.group(1).strip())

            fields = {u'Date' : u'inception',
                      u'Technique' : u'medium',
                      u'Dimensions' : u'dimensions',
                      u'Entry date' : u'acquisitiondate',
                      u'Register number' : u'id',
            }

            baseregex = u'\<div class\=\"field-label\"\>%s\:&nbsp;\<\/div\>\s*\n\s*\<div class\=\"field-items\"\>\s*\n\s*\<div class\=\"field-item even\">([^\<]+)\<\/div\>'
            for field in fields:
                valuematch = re.search(baseregex % (field,), itempage.text)
                if valuematch:
                    fieldvalue = valuematch.group(1).strip()
                    if field == u'Technique':
                        fieldvalue = fieldvalue.lower()
                        metadata[fields[field]] = htmlparser.unescape(fieldvalue)
                    elif field == u'Dimensions':
                        regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm'
                        regex_3d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm'
                        match_2d = re.match(regex_2d, fieldvalue)
                        match_3d = re.match(regex_3d, fieldvalue)
                        if match_2d:
                            metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                            metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                        elif match_3d:
                            metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                            metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                            metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')
                    else:
                        metadata[fields[field]] = htmlparser.unescape(fieldvalue)
                else:
                    print u'No match for %s' % (field,)



            metadata['idpid'] = u'P217'

            creatorregex = u'\<a href\=\"\/en\/coleccion\/autor\/[^\"]+\"\>\s*\n\s*([^\<]+)\<\/a\>\s*\<span class\=\"datos-biograficos\"\>'
            creatormatch = re.search(creatorregex, itempage.text)
            name = htmlparser.unescape(creatormatch.group(1).strip())
            metadata['creatorname'] = name
            metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', name,),
                                        u'en' : u'%s by %s' % (u'painting', name,),
                                        u'es' : u'%s de %s' % (u'cuadro', name,),
                                        }
            yield metadata




def main():
    dictGen = getSofiaGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
