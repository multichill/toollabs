#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Lenbachhaus to Wikidata.

Just loop over pages like https://sammlungonline.lenbachhaus.de/liste.html?tx_kesearch_pi1[page]=1&tx_kesearch_pi1[filter][1][267]=Gemälde

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getLenbachhausGenerator():
    """
    Generator to return Lenbachhaus paintings
    """
    gndPainters = getGndPaintersOnWikidata()
    gndnotfound = []
    basesearchurl = u'https://sammlungonline.lenbachhaus.de/liste.html?tx_kesearch_pi1[page]=%s&tx_kesearch_pi1[filter][1][267]=Gem%%C3%%A4lde'
    htmlparser = HTMLParser()

    # 564 hits, 25 per page

    for i in range(1, 24):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = requests.get(searchurl)

        workurlregex = u'\<a href\=\"(\/objekt\/[^\?]+\d+\.html)\?'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            url = u'https://sammlungonline.lenbachhaus.de%s' % (match.group(1),)
            metadata = {}

            itempage = requests.get(url)
            pywikibot.output(url)

            metadata['url'] = url

            metadata['collectionqid'] = u'Q262234'
            metadata['collectionshort'] = u'Lenbachhaus'
            metadata['locationqid'] = u'Q262234'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            invregex = u'\<div class\=\"mms_showspec mms_inventar\"\>[\r\n\t\s]*\<div class\=\"mms_spec_header\"\>Inventarnummer\<\/div\>[\r\n\t\s]*\<div class\=\"mms_spec_value\"\>\s*([^\<]+)\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            # Not sure if I need to replace space here
            metadata['id'] = htmlparser.unescape(invmatch.group(1).replace(u'&nbsp;', u' ')).strip()


            #titleregex = u'\<meta content\=\"([^\"]+)\" name\=\"og\:title\"\>'
            titleregex = u'\<div class\=\"mms_maincaption_row mms_title\"\>[\r\n\t\s]*\<div class\=\"mmmc_def mmmc_object_title\"\>Titel / Kurzbeschreibung\<\/div\>[\r\n\t\s]*\<div class\=\"mmmc_desc mmmc_object:name\"\>\s*([^\<]+)\<\/div\>'
            titlematch = re.search(titleregex, itempage.text)

            title = htmlparser.unescape(titlematch.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'de' : title,
                                  }

            creatoregex = u'\<a href\=\"(\/personen\/[^\?]+)\?[^\"]+"\>[\r\n\t\s]*\<div class\=\"mmmc_def mmmc_person_role\"\>Künstler_in\<\/div\>[\r\n\t\s]*\<div class\=\"mmmc_desc mmmc_person_name\"\>\s*([^\<]+)\<\/div\>'
            creatormatch = re.search(creatoregex, itempage.text)

            # Rare cases without a match
            if creatormatch:
                creatorurl = u'https://sammlungonline.lenbachhaus.de%s' % (creatormatch.group(1),)
                creatorname = htmlparser.unescape(creatormatch.group(2)).strip()

                metadata['creatorname'] = creatorname

                metadata['description'] = { u'nl' : u'%s van %s' % (u'schilderij', metadata.get('creatorname'),),
                                            u'en' : u'%s by %s' % (u'painting', metadata.get('creatorname'),),
                                            u'de' : u'%s von %s' % (u'Gemälde', metadata.get('creatorname'), ),
                                            u'fr' : u'%s de %s' % (u'peinture', metadata.get('creatorname'), ),
                                            }


                creatorpage = requests.get(creatorurl)
                gndregex = u'\<div class\=\"mms_maincaption_row mms_bio\"\>[\r\n\t\s]*\<div class\=\"mmmc_def mms_bio\"\>GND-Nr\.\<\/div\>[\r\n\t\s]*\<div class\=\"mmmc_desc mms_bio\"\>\<a href\=\"[^\"]+\" target\=\"_blank\"\>([^\<]+)\<\/a\>\<\/div\>'
                gndmatch = re.search(gndregex, creatorpage.text)
                if gndmatch:
                    gndid = gndmatch.group(1)
                    if gndid in gndPainters:
                        pywikibot.output (u'Found GND %s on %s' % (gndid, gndPainters.get(gndid)))
                        metadata['creatorqid'] = gndPainters.get(gndid)
                    else:
                        gndmisstext = u'No Wikidata item for %s with GND id %s on %s' % (creatorname, gndid, creatorurl)
                        pywikibot.output (gndmisstext)
                        gndnotfound.append(gndmisstext)
                else:
                    pywikibot.output(u'No GND found for %s on %s' % (creatorname, creatorurl))



            # Let's see if we can extract some dates. Json-ld is provided, but doesn't have circa and the likes
            dateregex = u'\<div class\=\"mms_showspec mms_date\"\>[\r\n\t\s]*\<div class\=\"mms_spec_header\"\>Datierung\<\/div\>[\r\n\t\s]*\<div class\=\"mms_spec_value\"\>\s*(\d\d\d\d)[\r\n\t\s]*\<\/div\>'
            datecircaregex = u'\<div class\=\"mms_showspec mms_date\"\>[\r\n\t\s]*\<div class\=\"mms_spec_header\"\>Datierung\<\/div\>[\r\n\t\s]*\<div class\=\"mms_spec_value\"\>\s*um (\d\d\d\d)[\r\n\t\s]*\<\/div\>'
            #periodregex = u'\<span class\=\"dsArtwork__titleYear\"\>,\s*(\d\d\d\d)\s*&ndash;\s*(\d\d\d\d)\<\/span\>'
            #circaperiodregex = u'\<span class\=\"dsArtwork__titleYear\"\>,\s*ca\.\s*(\d\d\d\d)\s*&ndash;\s*(\d\d\d\d)\<\/span\>'
            #shortperiodregex = u'\<meta content\=\"(\d\d)(\d\d)–(\d\d)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            #circashortperiodregex = u'\<p\>\<strong\>Date\<\/strong\>\<br\/\>c\.\s*(\d\d)(\d\d)–(\d\d)\<\/p\>'
            otherdateregex = u'\<div class\=\"mms_showspec mms_date\"\>[\r\n\t\s]*\<div class\=\"mms_spec_header\"\>Datierung\<\/div\>[\r\n\t\s]*\<div class\=\"mms_spec_value\"\>\s*([^\<]+)[\r\n\t\s]*\<\/div\>'

            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            periodmatch = None
            circaperiodmatch = None
            shortperiodmatch = None
            circashortperiodmatch = None
            otherdatematch = re.search(otherdateregex, itempage.text)

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
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # A bit of provenance data
            acquisitiondateregex = u'\<div class\=\"mms_showspec mms_inventar\"\>[\r\n\t\s]*\<div class\=\"mms_spec_header\"\>Zugang\<\/div\>[\r\n\t\s]*\<div class\=\"mms_spec_value\"\>[\r\n\t\s]*[^\<]+[\r\n\t\s]*(\d\d\d\d)[\r\n\t\s]*\<\/div\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            # Not doing, just says "Leinwand"
            #mediumregex = u'\<dt class\=\"dsProperty__caption\">Physical Description\<\/dt\>[\r\n\t\s]*\<dd class\=\"dsProperty__text\"\>\s*Oil on canvas,'
            #mediummatch = re.search(mediumregex, itempage.text)
            #if mediummatch:
            #    metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<div class\=\"mms_showspec mms_measures\"\>[\r\n\t\s]*\<div class\=\"mms_spec_header\"\>Maße\<\/div\>[\r\n\t\s]*\<div class\=\"mms_spec_value\"\>([^\<]*[\r\n\t\s]*[^\<]*)\<\/div\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'(?P<height>\d+(,\d+)?)\s*cm[\r\n\t\s]*x\s*(?P<width>\d+(,\d+)?)\scm'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')

            # To possible image locations, this seems to be the original upload other based on it
            imageregex = u'\<meta property\=\"og:image\" content\=\"([^\"]+)\"\ \/\>'
            imagematch = re.search(imageregex, itempage.text)
            if imagematch and u'https://creativecommons.org/licenses/by-sa/4.0/' in itempage.text:
                metadata[u'imageurl'] = imagematch.group(1)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
                metadata[u'imageoperatedby'] = u'Q262234'
                # Used this to add suggestions everywhere
                #metadata[u'imageurlforce'] = True

            yield metadata

    for missedline in sorted(set(gndnotfound)):
        pywikibot.output(missedline)

def getGndPaintersOnWikidata():
    """
    Return all the painters with a GND id
    :return: Dict
    """
    result = {}
    query = u'SELECT ?item ?id WHERE { ?item p:P106/ps:P106 wd:Q1028181 . ?item wdt:P227 ?id }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace(u'http://www.wikidata.org/entity/', u'')
        result[resultitem.get('id')] = qid
    return result


def main():
    dictGen = getLenbachhausGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
