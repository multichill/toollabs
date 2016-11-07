#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Prado ( https://www.museodelprado.es/en/the-collection/art-works ) to Wikidata.

This bot uses artdatabot to upload it to Wikidata

"""
import artdatabot
import pywikibot
import requests
import re
import HTMLParser
import time
import json

def getPradoGenerator():
    """
    Generator to return Lakenhal Museum paintings
    """
    basesearchurl = u'https://resultados4.museodelprado.es/CargadorResultados/CargarResultados?pUsarMasterParaLectura=false&pProyectoID=%227317a29a-d846-4c54-9034-6a114c3658fe%22&pEsUsuarioInvitado=true&pIdentidadID=%22FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF%22&pParametros=%22cidoc:p2_has_type@@@pm:objectTypeNode=http://museodelprado.es/items/objecttype_20|pagina=0%22&pLanguageCode=%22en%22&pPrimeraCarga=false&pAdministradorVeTodasPersonas=false&pTipoBusqueda=0&pNumeroParteResultados=1&pGrafo=%227317a29a-d846-4c54-9034-6a114c3658fe%22&pFiltroContexto=%22%22&pParametros_adiccionales=%22PestanyaActualID=c89fbb0c-a52c-4700-9220-79f4964d3949|rdf:type=pmartwork|orden=asc|ordenarPor=pm:relevance,ecidoc:p62_E52_p79_has_time-span_beginning,ecidoc:p62_E52_p80_has_time-span_end,gnoss:hasfechapublicacion%22&cont=0&format=json'

    #htmlparser = HTMLParser.HTMLParser()

    # Total results 1998, 18 per page
    for i in range(0, 112):
        print u'Working on search page %s' % (i,)
        searchurl = basesearchurl.replace(u'pagina=0', u'pagina=%s' % (i,))
        searchPage = requests.get(searchurl)
        # Yeah, let's pack crap HTML in json, that's fun!
        searchPageData = searchPage.json().get('Value')

        searchRegex = u'\<a href\=\"(https\:\/\/www\.museodelprado\.es\/en\/the-collection\/art-work\/[^\/]+\/[^\"]+)\"\>'
        matches = re.finditer(searchRegex, searchPageData)

        urls = []
        for match in matches:
            urls.append(match.group(1))

        for url in set(urls):
            print url
            itempage = requests.get(url)
            esurlregex = u'\<a class\=\"lang\" lalt\=\"Espa&#241;ol\" href\=\"(https\:\/\/www\.museodelprado\.es\/coleccion\/obra-de-arte\/[^\/]+\/[^\"]+)\"\>\<span\>es\<\/span\>\<\/a\>'
            esurlmatch = re.search(esurlregex, itempage.text)
            if not esurlmatch:
                # So probably something went wrong. Let's wait and try again
                print u'Did not find esurl on %s, waiting and trying again' % (url,)
                time.sleep(60)
                itempage = requests.get(url)
                esurlmatch = re.search(esurlregex, itempage.text)

            esurl = esurlmatch.group(1)
            esitempage = requests.get(esurl)
            embededjsonregex = u'\<script type\=\"application\/ld\+json\"\>\n\s*(\{\".+)\n\<\/script\>'
            try:
                jsondata = json.loads(re.search(embededjsonregex, itempage.text).group(1))
                esjsondata = json.loads(re.search(embededjsonregex, esitempage.text).group(1))
            except ValueError:
                # Some descriptions seem to contain junk. We're not using it anyway so throw it out
                emptydescregex = u'\"description\"\:\s*\"[^\"]+\",'
                emptydesc = u'"description":  " ",'
                cleanedup = re.sub(emptydescregex, emptydesc, re.search(embededjsonregex, itempage.text).group(1))
                jsondata = json.loads(cleanedup)
                escleanedup = re.sub(emptydescregex, emptydesc, re.search(embededjsonregex, esitempage.text).group(1))
                esjsondata = json.loads(escleanedup)

            metadata = {}

            metadata['collectionqid'] = u'Q160112'
            metadata['collectionshort'] = u'Prado'
            metadata['locationqid'] = u'Q160112'
            metadata['instanceofqid'] = u'Q3305213'

            metadata['url'] = url

            metadata['title'] = {}
            if jsondata.get('name'):
                metadata['title'][u'en'] = jsondata.get('name')
            if esjsondata.get('name'):
                metadata['title'][u'es'] = esjsondata.get('name')

            metadata['idpid'] = u'P217'
            metadata['id'] = jsondata.get('artEdition')

            if isinstance(jsondata.get('author'), dict):
                name = jsondata.get('author').get('name')
            else:
                name = jsondata.get('author')[0].get('name')
            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)

            if isinstance(esjsondata.get('author'), dict):
                esname = esjsondata.get('author').get('name')
            else:
                esname = esjsondata.get('author')[0].get('name')

            if u',' in esname:
                (surname, sep, firstname) = esname.partition(u',')
                esname = u'%s %s' % (firstname.strip(), surname.strip(),)

            if name==u'Anonymous':
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
                                            u'es' : u'%s de %s' % (u'cuadro', esname,),
                                            }

            # Inception is a bit messy in the json. Not using it
            # metadata['inception'] = ....

            if jsondata.get('artworkSurface') == u'Canvas' and jsondata.get('artform') == u'Oil':
                metadata['medium'] = u'oil on canvas'
            if jsondata.get('height'):
                metadata['heightcm'] = jsondata.get('height').get(u'value')
            if jsondata.get('width'):
                metadata['widthcm'] = jsondata.get('width').get(u'value')

            # Yeah! They have decent resolution images
            metadata['imageurl'] = jsondata.get('image')
            yield metadata
    
def main():
    dictGen = getPradoGenerator()

    # for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
