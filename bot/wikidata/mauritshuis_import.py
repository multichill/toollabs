#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Mauritshuis (Q221092) to Wikidata.

Just loop over pages like https://www.mauritshuis.nl/en/explore/the-collection/search/?mh_soort_object&category=collectie&pagina=2
or actually the json that's under it:
https://www.mauritshuis.nl/en/mapi/zoeken/zoek?categorie=collectie&query=&hasHistory=true&mh_soort_object=7d92939e170e46a595198d756d6919b1&pagina=63


This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getMauritshuisGenerator():
    """
    Generator to return Frans Hals Museum paintings
    """
    htmlparser = HTMLParser.HTMLParser()
    searchnlurl = u'https://www.mauritshuis.nl/nl-nl/mapi/zoeken/zoek?categorie=collectie&query=&pagina=70&mh_soort_object[]=7d92939e170e46a595198d756d6919b1&object_nummer='
    searchenurl = u'https://www.mauritshuis.nl/en/mapi/zoeken/zoek?categorie=collectie&query=&hasHistory=true&mh_soort_object=7d92939e170e46a595198d756d6919b1&pagina=70'

    searchnlPage = requests.get(searchnlurl)
    searchenPage = requests.get(searchenurl)

    nlcollection = searchnlPage.json().get('collectie')
    encollection = searchenPage.json().get('collectie')
    pywikibot.output(u'I found %s & %s items to work on, I expected at least 748 items' % (len(nlcollection),
                                                                                           len(encollection),
                                                                                           ))
    items = {}
    nlinvregex = u'^http\:\/\/www\.mauritshuis\.nl\/nl-nl\/verdiep\/de-collectie\/kunstwerken\/([^\d]+[^l^\d]|.+-)(l?\d+)/$'
    eninvregex = u'^http\:\/\/www\.mauritshuis\.nl\/en\/verdiep\/de-collectie\/kunstwerken\/([^\d]+[^l^\d]|.+-)(l?\d+)/$'
    for nlitem in nlcollection:
        nlurl = nlitem.get('url')
        nlinvmatch = re.match(nlinvregex, nlurl)
        nlinv = nlinvmatch.group(2)
        if items.get(nlinv):
            print u'something went wrong'
            print items.get(nlinv)
            time.sleep(10)
        items[nlinv] = {}
        items[nlinv]['nl']=nlitem
    for enitem in encollection:
        enurl = enitem.get('url')
        eninvmatch = re.match(eninvregex, enurl)
        eninv = eninvmatch.group(2)
        items[eninv]['en']=enitem

    for idnum, dualitem in items.items():

        metadata = {}

        nlitem = dualitem.get(u'nl')
        enitem = dualitem.get(u'en')

        #if len(item.get(u'authors')) > 2:
        #    print item.get(u'url')
        #    print u'LOOOOOOOONG'
        #    time.sleep(5)
        #print len(item.get(u'authors'))
        nlurl = nlitem.get(u'url').replace(u'http://www.mauritshuis.nl', u'https://www.mauritshuis.nl')
        nldetailurl = u'%sdetailgegevens/' % (nlurl,)

        # Museum site probably doesn't like it when we go fast
        # time.sleep(5)

        pywikibot.output(nldetailurl)

        itempage = requests.get(nldetailurl)
        metadata['url'] = nlurl

        metadata['collectionqid'] = u'Q221092'
        metadata['collectionshort'] = u'Mauritshuis'
        metadata['locationqid'] = u'Q221092'

        #No need to check, I'm actually searching for paintings.
        metadata['instanceofqid'] = u'Q3305213'

        # Good old regex to extract this
        invnumregex = u'\<div class\=\"component-key-value-set\"\>[\s\t\r\n]*\<div class\=\"key\"\>Inventaris nummer\</div\>[\s\t\r\n]*\<div class\=\"value\"\>[\s\t\r\n]*([^<]+)[\s\t\r\n]*\<\/div\>'
        invnumatch = re.search(invnumregex, itempage.text)
        metadata['idpid'] = u'P217'
        metadata['id'] = htmlparser.unescape(invnumatch.group(1).strip())

        metadata['title'] = { u'nl' : nlitem.get('titel'),
                              u'en' : enitem.get('titel'),
                              }

        anoniemregex = u'^([^\(]+)\(([^\)]+)\)$'
        if len(nlitem.get(u'authors'))==1:
            nlanoniemmatch = re.match(anoniemregex, nlitem.get(u'authors')[0])
            enanoniemmatch = re.match(anoniemregex, enitem.get(u'authors')[0])

            if nlitem.get(u'authors')[0].startswith(u'Anoniem'):
                metadata['creatorqid'] = u'Q4233718'
                metadata['description'] = { u'en' : u'painting by %s' % (enitem.get(u'authors')[0], ),
                                            u'nl' : u'schilderij van %s' % (nlitem.get(u'authors')[0], ),
                                            }

            elif nlanoniemmatch and enanoniemmatch:
                metadata['description'] = { u'en' : u'painting %s %s' % (enanoniemmatch.group(2).strip(),
                                                                         enanoniemmatch.group(1).strip(),),
                                            u'nl' : u'schilderij %s %s' % (nlanoniemmatch.group(2).strip(),
                                                                        nlanoniemmatch.group(1).strip(),),
                                            }
            else:
                metadata['description'] = { u'en' : u'painting by %s' % (enitem.get(u'authors')[0], ),
                                            u'nl' : u'schilderij van %s' % (nlitem.get(u'authors')[0], ),
                                            }
        elif len(nlitem.get(u'authors'))==2:
            metadata['description'] = { u'en' : u'painting by %s & %s' % (enitem.get(u'authors')[0],
                                                                          enitem.get(u'authors')[1]),
                                        u'nl' : u'schilderij van %s & %s' % (nlitem.get(u'authors')[0],
                                                                             nlitem.get(u'authors')[1],),
                                        }
        else:
            metadata['description'] = { u'en' : u'painting by %s, %s & %s' % (enitem.get(u'authors')[0],
                                                                              enitem.get(u'authors')[1],
                                                                              enitem.get(u'authors')[2]),
                                        u'nl' : u'schilderij van %s, %s & %s' % (nlitem.get(u'authors')[0],
                                                                                 nlitem.get(u'authors')[1],
                                                                                 nlitem.get(u'authors')[2]),
                                        }

        metadata['inception'] = nlitem.get(u'periode')

        dimensionregex = u'\<div class\=\"component-key-value-set\"\>[\s\t\r\n]*\<div class\=\"key\"\>Afmetingen\<\/div\>[\s\t\r\n]*\<div class\=\"value\">hoogte\:\s*(?P<height>\d+(,\d+)?)\s*cm[\s\t\r\n]*\<br \/\>breedte\:\s*(?P<width>\d+(,\d+)?)\s*cm[\s\t\r\n]*\<\/div\>'
        dimensionmatch = re.search(dimensionregex, itempage.text)
        if dimensionmatch:
            metadata['heightcm'] = dimensionmatch.group(u'height').replace(u',', u'.')
            metadata['widthcm'] = dimensionmatch.group(u'width').replace(u',', u'.')


        herkomstregex = u'\<div class\=\"component-key-value-set\"\>[\s\t\r\n]*\<div class\=\"key\"\>Herkomst\<\/div\>[\s\t\r\n]*\<div class\=\"value\"\>[\s\t\r\n]*([^\<]+)[\s\t\r\n]*\<\/div\>'
        herkomstmatch = re.search(herkomstregex, itempage.text)
        if herkomstmatch:
            if u'Rijksmuseum, Amsterdam' in herkomstmatch.group(1):
                metadata[u'extracollectionqid'] = u'Q190804'

        # Can't really find dates in a format I can parse
        # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

        oiloncanvasregex = u'\<div class\=\"component-key-value-set\"\>[\s\t\r\n]*\<div class\=\"key\"\>Techniek\<\/div\>[\s\t\r\n]*\<div class\=\"value\"\>olieverf\<\/div\>[\s\t\r\n]*\<\/div\>[\s\t\r\n]*\<div class\=\"component-key-value-set\"\>[\s\t\r\n]*\<div class\=\"key\"\>Materiaal\<\/div\>[\s\t\r\n]*\<div class\=\"value\"\>doek\<\/div\>'
        oiloncanvasmatch = re.search(oiloncanvasregex, itempage.text)

        # Only return if a valid medium is found
        if oiloncanvasmatch:
            metadata['medium'] = u'oil on canvas'
        yield metadata


def main():
    dictGen = getMauritshuisGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
