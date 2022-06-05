#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Stichting Nederlands Kunstbezit (Q28045665) to Wikidata.

Just loop over pages like http://herkomstgezocht.nl/nl/search/collection?page=1&f[0]=type%3Ank_record&f[1]=field_objectaanduiding%3A11621

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import html

def getSNKGenerator():
    """
    Generator to return  Stichting Nederlands Kunstbezit paintings
    """
    mediums = { 'olieverf op doek' : 'oil on canvas',
                'olieverf op paneel' : 'oil on panel',
                'olieverf op koper' : 'oil on copper',
                'tempera op paneel' : 'tempera on panel',
                }

    genres = { 'portret' : 'Q134307',
               'stilleven' : 'Q170571',
               'allegorie' : 'Q2839016',
               'heilige' : 'Q2864737',
               'bijbelse voorstelling' : 'Q2864737',
               'bijbelse voorstelling, heilige' : 'Q2864737',
               'landschap' : 'Q191163',
               'genre' : 'Q1047337',
               'mythologie' : 'Q3374376',
               'marine' : 'Q158607',
               }

    basesearchurl = u'http://herkomstgezocht.nl/nl/search/collection?f[0]=type%%3Ank_record&f[1]=field_objectaanduiding%%3A11621&page=%s'

    # 1614 results, 15 per page (starting at 0)
    for i in range(0, 108):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        urlregex = u'\<a class\=\"read-more\" href\=\"(http\:\/\/herkomstgezocht\.nl\/nl\/nk-collectie\/[^\"]+)\"\>read more\<\/a\>'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = match.group(1)

            pywikibot.output(url)

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q28045665'
            metadata['collectionshort'] = 'SNK'
            # No location, it's a meta collection
            # metadata['locationqid'] = u'Q238587'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            # Let's see if this one works or if we have to make it a bit more liberal
            invregex = u'\<div class\=\"field field-name-field-icn-inventarisnummer\"\>(NK\d+[^\<]*)\<\/div\>'
            invmatch = re.search(invregex, itempage.text)

            metadata['idpid'] = 'P217'
            metadata['id'] = invmatch.group(1).strip()

            titleregex = u'\<div class\=\"field field-name-title-field\"\>\<h1\>([^\<]+)\<\/h1\>'
            titlematch = re.search(titleregex, itempage.text)

            title = html.unescape(titlematch.group(1).strip())

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'nl' : title,
                                  }
            creatorregex = u'\<div class\=\"field field-name-field-kunstenaar-tax field-type-taxonomy-term-reference field-label-hidden\"\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>([^\<]+)\<\/div\>'
            creatormatch = re.search(creatorregex, itempage.text)
            if creatormatch:
                name = html.unescape(creatormatch.group(1).strip())
                if u',' in name:
                    (surname, sep, firstname) = name.partition(u',')
                    name = u'%s %s' % (firstname.strip(), surname.strip(),)

            # Works after/copy/etc.
            typeringregex = u'\<div class\=\"field field-name-field-typering field-type-taxonomy-term-reference field-label-hidden\"\>\<div class\=\"field-items\"\>\<div class\=\"field-item even\"\>([^\<]+)\<\/div\>'
            typeringmatch = re.search(typeringregex, itempage.text)

            if not creatormatch:
                metadata['creatorname'] = u'unknown artist'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            elif typeringmatch:
                typering = typeringmatch.group(1)
                metadata['creatorname'] = u'unknown artist'
                metadata['description'] = { u'nl' : u'schilderij %s %s' % (typering, name),
                                            }
                metadata['creatorqid'] = u'Q4233718'
            else:
                metadata['creatorname'] = name
                metadata['description'] = { u'en' : u'painting by %s' % (name, ),
                                            u'nl' : u'schilderij van %s' % (name, ),
                                            }
            # Old works, dating are rarely years
            # metadata['inception'] = datematch.group(1)

            # No date known, most of it will be 1946. Or should I use the "aangifte"? Not sure
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            medium_regex = u'\<div class\=\"field field-name-field-materiaal-techniek\"\>([^\<]+)\<\/div\>'
            medium_match = re.search(medium_regex, itempage.text)

            if medium_match:
                medium = medium_match.group(1).lower()
                if medium in mediums:
                    metadata['medium'] = mediums.get(medium)
                else:
                    print (medium)

            # <div class="field field-name-field-trefwoord">portret</div>

            genre_regex = u'\<div class\=\"field field-name-field-trefwoord\"\>([^\<]+)\<\/div\>'
            genre_match = re.search(genre_regex, itempage.text)

            if genre_match:
                genre = genre_match.group(1).lower()
                if genre in genres:
                    metadata['genreqid'] = genres.get(genre)
                else:
                    print (genre)

            heightregex = u'\<div class=\"field field-name-field-hoogte-lengte\"\>(\d+\.\d+)\<\/div\>'
            heightmatch = re.search(heightregex, itempage.text)
            if heightmatch:
                metadata['heightcm'] = heightmatch.group(1).strip()

            widthregex = u'\<div class=\"field field-name-field-breedte\"\>(\d+\.\d+)\<\/div\>'
            widthmatch = re.search(widthregex, itempage.text)
            if widthmatch:
                metadata['widthcm'] = widthmatch.group(1).strip()

            # Extract some more provenance data
            goering_regex = '\<div class\=\"field field-name-field-herkomstnaam-tax\"\>Göring, H\.\<\/div\>'
            goering_match = re.search(goering_regex, itempage.text)

            if goering_match:
                metadata['extracollectionqid'] = 'Q2647884'

            linz_regex = '\<div class\=\"field field-name-field-herkomstnaam-tax\"\>Führermuseum\<\/div\>'
            linz_match = re.search(linz_regex, itempage.text)

            if linz_match:
                metadata['extracollectionqid2'] = 'Q475667'

            yield metadata


def main(*args):
    dict_gen =  getSNKGenerator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dict_gen:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()

if __name__ == "__main__":
    main()