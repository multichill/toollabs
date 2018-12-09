#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Musée national des beaux-arts du Québec to Wikidata.

Use graphql based api to get the data


"""
import artdatabot
import pywikibot
import requests
import re
import time
import json
try:
    from html.parser import HTMLParser
except ImportError:
    import HTMLParser

def getQuebecBaGenerator():
    """
    Generator to return Musée national des beaux-arts du Québec paintings
    """

    data = """{"operationName":null,"variables":{"locale":"en","page":1,"limit":36,"searchParams":{"categories":["Peinture"]}},"query":""}"""

    postjson = {""" "operationName" : null,
                "variables" : { "locale" : "en",
                                "page" : 1,
                                "limit" : 36,
                                "searchParams" : { "categories" :["Peinture"]}
                                },
                "query" : "mutation ($page: Int, $limit: Int, $searchParams: SearchParams!) {search(page: $page, limit: $limit, searchParams: $searchParams) }"
                """}

    #postjson = data)



    postjson = {'query': """{ search(page: 1, limit: 10, searchParams: "Peinture") }"""} # , searchParams: { "categories" :["Peinture"]}
    #postjson = {'query': """search(searchParams:{categories:[Peinture] } )"""}
    postjson = {"query": "query{ artwork(id: 600050061) {id name} } "} # <- Deze doet het!
    #postjson = {"query": "query{ artwork(mimsyCategory: Peinture) {id name} } "} #
    postjson = {'query' : """query { similarArtworks(like: 600050061, unlike: [], limit: 6) { similarArtworks { id name imageRights onExhibit isFavorite artists { name __typename } mainUpload { mediaUrl mediaType __typename } __typename } __typename } } """,}

    postjson = {'query' : """query { search(page: 1, limit: 36, searchParams: { categories: { Peinture } } ) { page resultCount }""",}


    headers = { "Accept" : "*/*",
                "origin" : "https://collections.mnbaq.org",
                "Referer" : "https://collections.mnbaq.org/en/search",
                "Content-type": "application/json",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0",
                }
    basesearchurl = u'https://api.collections.mnbaq.org/graphql'

    htmlparser = HTMLParser()

    for i in range(1, 104): # 3993 works with 36 per page
        postjson = {"operationName":None,
                 "variables" : { "locale" : "en",
                                 "page" : i,
                                 "limit" : 36,
                                 "searchParams" : {
                                     "type" : "artwork",
                                     "categories" :["Peinture"]
                                 }
                                 },
                 "query":"""mutation ($page: Int, $limit: Int, $searchParams: SearchParams!) {
  search(page: $page, limit: $limit, searchParams: $searchParams) {
    page
    limit
    resultCount
    results {
      content {
        __typename
        ... on Artwork {
          __typename
          id
          inventoryNumber
          materials
          measurements
          productionDate
          name
          imageRights
          artists {
            name
            __typename
          }
          mainUpload {
            mediaUrl
            mediaType
            __typename
          }
        }
        ... on Artist {
          __typename
          name
          id
          mainUpload {
            mediaUrl
            mediaType
            __typename
          }
        }
        ... on Album {
          __typename
          id
          name
          categories {
            name
            __typename
          }
          albumCover {
            mainUpload {
              mediaUrl
              mediaType
              __typename
            }
            __typename
          }
        }
      }
      __typename
    }
    __typename
  }
}
"""}

        searchpage = requests.post(basesearchurl, data=json.dumps(postjson), headers=headers)

        #print(json.dumps(searchpage.json(), indent=4, sort_keys=True))



        for searchresult in searchpage.json().get("data").get("search").get("results"):
            iteminfo = searchresult.get("content")
            #print(json.dumps(iteminfo, indent=4, sort_keys=True))
            #time.sleep(5)

            metadata = {}
            url = 'https://collections.mnbaq.org/en/artwork/%s' % iteminfo.get('id')
            print (url)

            metadata['url'] = url
            metadata['collectionqid'] = u'Q2338135'
            metadata['collectionshort'] = u'MNBAQ'
            metadata['locationqid'] = u'Q2338135'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            metadata['id'] = iteminfo.get('inventoryNumber')

            title = iteminfo.get('name')
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]

            # The mix up English and French everywhere. We might as well do the same
            metadata['title'] = { u'en' : title,
                                  u'fr' : title,
                                  }

            name = iteminfo.get('artists')[0].get('name')

            if u',' in name:
                (surname, sep, firstname) = name.partition(u',')
                name = u'%s %s' % (firstname.strip(), surname.strip(),)


            if name==u'Inconnu':
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = "Q4233718"
            else:
                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                            u'en' : u'painting by %s' % (name, ),
                                            u'de' : u'Gemälde von %s' % (name, ),
                                            u'fr' : u'peinture de %s' % (name, ),
                                            }

            if iteminfo.get('productionDate'):
                datecircaregex = u'^vers (\d\d\d\d)$'
                datecircamatch = re.match(datecircaregex, iteminfo.get('productionDate'))
                if datecircamatch:
                    metadata['inception'] = datecircamatch.group(1).strip()
                    metadata['inceptioncirca'] = True
                else:
                    metadata['inception'] = iteminfo.get('productionDate')

            # Doesn't seem to be available (could strip from inventory number)
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            if iteminfo.get('materials') and iteminfo.get('materials')==u'Huile sur toile':
                metadata['medium'] = u'oil on canvas'

            if iteminfo.get('measurements'):
                measurementstext = iteminfo.get('measurements')
                regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm'
                regex_3d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(',', '.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(',', '.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(',', '.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(',', '.')

            # Image is available, but not free
            #imageurlregex = u'\<link rel\=\"image_src\" href\=\"([^\"]+jpg)\" \/\>'
            #imageurlmatch = re.search(imageurlregex, itempage.text)
            #if imageurlmatch:
            #    metadata[u'imageurl'] = imageurlmatch.group(1)
            #    metadata[u'imageurlformat'] = u'Q2195' #JPEG
            #    #metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa-4.0
            #    # Could use this later to force
            #    metadata[u'imageurlforce'] = False

            # No IIIF
            yield metadata


def main():
    dictGen = getQuebecBaGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
