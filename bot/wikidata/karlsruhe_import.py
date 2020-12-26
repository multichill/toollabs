#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Kunsthalle Karlsruhe to Wikidata.

Just loop over pages like https://www.kunsthalle-karlsruhe.de/sammlung/alle-werke/?q=objektbezeichnung+all+%22Gem%C3%A4lde%22
( https://www.kunsthalle-karlsruhe.de/wp-json/skk/v1/imdas-proxy/?qry=objektbezeichnung+all+%22Gem%C3%A4lde%22&fmt=json&fst=0&len=15&srt=meisterwerk&_=1608931583480 )


This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re

def getKarlsruhuGenerator():
    """
    Generator to return Karlsruhe paintings
    """
    aklartists = aklOnlineArtistsOnWikidata()
    missedakl = {}

    basesearchurl = 'https://www.kunsthalle-karlsruhe.de/wp-json/skk/v1/imdas-proxy/?qry=objektbezeichnung+all+%%22Gem%%C3%%A4lde%%22&fmt=json&fst=%s&len=%s&srt=meisterwerk&_=1608931583480'

    session = requests.Session()

    size = 100
    for i in range(0,2000,size):
        searchurl = basesearchurl % (i,size)
        print (searchurl)
        searchPage = session.get(searchurl)

        for record in searchPage.json().get('records'):
            metadata = {}
            # We first need to extract the creator and the title before we can build the url
            # See function ImdasModel in https://www.kunsthalle-karlsruhe.de/build/app-e23ffb65bc.js

            creatorname = None
            aklid = None
            aklregex = 'AKL\:[\n]*Ident\.-Nr\.\:\s*(\d+[^\n]+)\n'
            for person in record.get('personen'):
                if person.get('rolle') == 'Künstler':
                    creatorname = person.get('anzeigename')
                    if person.get('notiz'):
                        aklmatch = re.search(aklregex, person.get('notiz'))
                        if aklmatch:
                            # AKL is a bit unclear, incomplete and broken links. No noisy output
                            aklid = aklmatch.group(1).replace(',', '')
                            pywikibot.output('Found AKL id %s' % (aklid,))
                        else:
                            pywikibot.output('Notiz "%s" did not match' % (person.get('notiz'),))
                    break
            if not creatorname:
                creatorname = 'Unbekannt'

            title = record.get('objekttitel')
            imdasid = record.get('imdasid')

            # Construct something like https://www.kunsthalle-karlsruhe.de/kunstwerke/Jacob-Jordaens/Moses-schl%C3%A4gt-Wasser-aus-dem-Felsen/60A3FF0741FC6B93869F828C4ACF70BA/
            url = 'https://www.kunsthalle-karlsruhe.de/kunstwerke/%s/%s/%s/' % (cleanUrlString(creatorname),
                                                                                cleanUrlString(title),
                                                                                imdasid,)

            pywikibot.output (url)

            metadata['url'] = url
            metadata['collectionqid'] = 'Q658725'
            metadata['collectionshort'] = 'Karlsruhe'
            metadata['locationqid'] = 'Q658725'

            # Search is for paintings
            metadata['instanceofqid'] = 'Q3305213'

            title = title.strip()

            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'de' : title,
                                  }

            metadata['idpid'] = 'P217'
            metadata['id'] = record.get('inventarnummer')

            metadata['creatorname'] = creatorname
            metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                        'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                        'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                        'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                        }

            if aklid:
                if aklid in aklartists:
                    pywikibot.output ('Found AKL Online id %s on %s' % (aklid, aklartists.get(aklid)))
                    metadata['creatorqid'] = aklartists.get(aklid)
                else:
                    akltuple = (aklid, creatorname)
                    if akltuple not in missedakl:
                        missedakl[akltuple] = 0
                    missedakl[akltuple] += 1
                    pywikibot.output('Missed %s for %s' % akltuple)


            # Extract it from the written text
            if record.get('entstehungszeit'):
                dateregex = '^(\d\d\d\d)\s*$'
                datecircaregex = '^um\s*(\d\d\d\d)\s*$'
                periodregex = '^(\d\d\d\d)[-\/](\d\d\d\d)\s*$'
                circaperiodregex = '^um\s*(\d\d\d\d)[-\/](\d\d\d\d)\s*$'
                shortperiodregex = '^(\d\d)(\d\d)[-\/](\d\d)\s*$'
                circashortperiodregex = '^um\s*(\d\d)(\d\d)[-\/](\d\d)\s*$'

                datematch = re.search(dateregex, record.get('entstehungszeit'))
                datecircamatch = re.search(datecircaregex, record.get('entstehungszeit'))
                periodmatch = re.search(periodregex, record.get('entstehungszeit'))
                circaperiodmatch = re.search(circaperiodregex, record.get('entstehungszeit'))
                shortperiodmatch = re.search(shortperiodregex, record.get('entstehungszeit'))
                circashortperiodmatch = re.search(circashortperiodregex, record.get('entstehungszeit'))

                if datematch:
                    metadata['inception'] = int(datematch.group(1).strip())
                elif datecircamatch:
                    metadata['inception'] = int(datecircamatch.group(1).strip())
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1))
                    metadata['inceptionend'] = int(periodmatch.group(2))
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1))
                    metadata['inceptionend'] = int(circaperiodmatch.group(2))
                    metadata['inceptioncirca'] = True
                elif shortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (shortperiodmatch.group(1),shortperiodmatch.group(3),))
                elif circashortperiodmatch:
                    metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                    metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                    metadata['inceptioncirca'] = True
                else:
                    print ('Could not parse date: "%s"' % (record.get('entstehungszeit'),))

            # acquisitiondate not available
            # acquisitiondateRegex = u'\<em\>Acknowledgement\<\/em\>\:\s*.+(\d\d\d\d)[\r\n\t\s]*\<br\>'
            #acquisitiondateMatch = re.search(acquisitiondateRegex, itemPageData)
            #if acquisitiondateMatch:
            #    metadata['acquisitiondate'] = acquisitiondateMatch.group(1)

            # The API does output the material (canvas), but not the Technik (oil painting).
            # Don't feel like scraping. I'll just do a pass with a search on technik and material
            # https://www.kunsthalle-karlsruhe.de/sammlung/alle-werke/?q=technik+all+%22%C3%96lfarbe%22+and+material+all+%22Leinwand%22
            #    metadata['medium'] = u'oil on canvas'

            if record.get('genre'):
                religiouskeys = ['Bibel', 'Christuskind', 'Jesuskind', 'Beweinung Christi', 'Kreuzabnahme', 'Kreuzigung', 'Maria']
                if record.get('genre')=='Historie' and record.get('schlagworte'):
                    for schalgwort in record.get('schlagworte'):
                        if schalgwort.get('term') in religiouskeys:
                            metadata['genreqid'] = 'Q2864737' # religious art
                            break
                    #if not metadata.get('genreqid'):
                    #    print (record.get('schlagworte'))
                elif record.get('genre')=='Porträt':
                    metadata['genreqid'] = 'Q134307' # portrait
                elif record.get('genre')=='Landschaft':
                    metadata['genreqid'] = 'Q191163' # landscape art
                elif record.get('genre')=='Stillleben':
                    metadata['genreqid'] = 'Q170571' # still life
                elif record.get('genre')=='Allegorie':
                    metadata['genreqid'] = 'Q2839016' # allegory
                elif record.get('genre')=='Genre':
                    metadata['genreqid'] = 'Q1047337' # genre art
                elif record.get('genre')=='Seestück':
                    metadata['genreqid'] = 'Q158607' # marine art

            # Different kind of measurements. We want the carrier, not the frame
            if record.get('masse'):
                for masse in record.get('masse'):
                    if masse.get('teil') and masse.get('teil') == 'Bildträger' and masse.get('einheit') == 'cm':
                        if masse.get('typ') == 'Höhe':
                            metadata['heightcm'] = masse.get('wert').replace(',', '.')
                        elif masse.get('typ') == 'Breite':
                            metadata['widthcm'] = masse.get('wert').replace(',', '.')
                        elif masse.get('typ') == 'Tiefe':
                            metadata['depthcm'] = masse.get('wert').replace(',', '.')

            # They provide CC0 images!
            if record.get('bilder'):
                if record.get('bilder')[0].get('rechte') == 'Staatliche Kunsthalle Karlsruhe':
                    metadata['imageurl'] = 'https://www.kunsthalle-karlsruhe.de/wp-content/kunstwerk/original/K%s.jpg' % (imdasid,)
                    metadata['imageurlformat'] = 'Q2195' # JPEG
                    metadata['imageoperatedby'] = 'Q658725'
                    metadata['imageurllicense'] = 'Q6938433' # CC0
                    # Used this to add suggestions everywhere
                    metadata['imageurlforce'] = True

            yield metadata

    for akltuple in missedakl:
        line = '%s - %s' % akltuple
        line += ' - %s' % (missedakl.get(akltuple))
        pywikibot.output(line)


def aklOnlineArtistsOnWikidata():
    """
    Just return all the AKL Online artist ID people as a dict
    :return: Dict
    """
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:P4432 ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result

def cleanUrlString(toclean):
    """
    Funky function like cleanUrlString in https://www.kunsthalle-karlsruhe.de/build/app-e23ffb65bc.js
    :param toclean: The string to clean
    :return: Cleaned up string
    """
    regex = '[^A-Za-zÄäÖöÜüßéèêÈÉ\'\-]'
    result = re.sub(regex, ' ', toclean)
    result = result.replace(' ', ' ')
    result = result.replace(' ', ' ')
    result = result.replace(' ', ' ')
    result = result.strip()
    result = result.replace(' ', '-')
    return result

def main(*args):
    dictGen = getKarlsruhuGenerator()
    dryrun = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True
        elif arg.startswith('-create'):
            create = True

    if dryrun:
        for painting in dictGen:
            print (painting)
    else:
        artDataBot = artdatabot.ArtDataBot(dictGen, create=create)
        artDataBot.run()

if __name__ == "__main__":
    main()
