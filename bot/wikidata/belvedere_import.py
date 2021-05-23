#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Österreichische Galerie Belvedere in Vienna to Wikidata.

Just loop over pages like https://sammlung.belvedere.at/advancedsearch/Objects/classifications%3AMalerei/images?page=1

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getBelvedereGenerator():
    """
    Generator to return Belvedere paintings
    """
    #basesearchurl = u'http://digital.belvedere.at/advancedsearch/objects/name:Gemälde/images?page=%s'
    # This one is for all the paintings
    basesearchurl = 'https://sammlung.belvedere.at/advancedsearch/Objects/classifications%%3AMalerei/images?page=%s'
    # Leftovers
    #basesearchurl = u'https://sammlung.belvedere.at/advancedsearch/Objects/name%%3ATafelbild/images?page=%s'
    htmlparser = HTMLParser()

    for i in range(1, 422): #12): # 341):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        urlregex = 'data-a2a-url\=\"(https?:\/\/sammlung\.belvedere\.at\/objects\/(\d+)\/[^\"]+)\;jsessionid\=[^\"]+\"'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = match.group(1)

            metadata['artworkidpid'] = 'P5823'
            metadata['artworkid'] = match.group(2)

            # Museum site doesn't seem to like it when we go fast
            #time.sleep(15)

            pywikibot.output(url)
            try:
                itempage = requests.get(url)
            except requests.exceptions.ConnectionError:
                time.sleep(60)
                itempage = requests.get(url)

            metadata['url'] = url
            metadata['collectionqid'] = 'Q303139'
            metadata['collectionshort'] = 'Belvedere'
            metadata['locationqid'] = 'Q303139'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'

            metadata['idpid'] = 'P217'
            invregex = '\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldLabel\"\>Inventarnummer\s*\<\/span\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            if invmatch:
                metadata['id'] = invmatch.group(1).strip()
            else:
                pywikibot.output('Something went wrong, no inventory number found, skipping this one')
                continue

            titleregex = '\<div class\=\"detailField titleField\"\>\<h1 property\=\"name\" itemprop\=\"name\"\>([^\<]+)\<\/h1\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1).strip())
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'de' : title,
                                  }
            # This one is not complete, attributed works will be missed
            # creatorregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema:creator\" itemprop\=\"creator\"\>'
            creatorregex = '\<span class\=\"detailFieldLabel\"\>Künstler\/in\<\/span\>\<span class\=\"detailFieldValue\"\>\<span class\=\"mr-1\"\>\<a property\=\"url\" itemprop=\"url\" href\=\"\/people\/\d+\/[^\"]+\"\>\<span property\=\"name\" itemprop\=\"name\"\>[\r\n\t\s]*([^\<]+)[\r\n\t\s]*\<\/span\>'
            creatormatch = re.search(creatorregex, itempage.text)
            if creatormatch:
                name = htmlparser.unescape(creatormatch.group(1).strip())

                metadata['creatorname'] = name
                metadata['description'] = { 'nl' : 'schilderij van %s' % (name, ),
                                            'en' : 'painting by %s' % (name, ),
                                            'de' : 'Gemälde von %s' % (name, ),
                                            }
            else:
                metadata['creatorname'] = 'anonymous'
                metadata['description'] = { 'nl' : 'schilderij van anonieme schilder',
                                            'en' : 'painting by anonymous painter',
                                        }
                metadata['creatorqid'] = 'Q4233718'

            # Was broken too
            dateregex = '\<span class\=\"detailFieldLabel\"\>Datierung\s*\<\/span\>\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)\<br\>\<\/span\>'
            datecircaregex = '\<span class\=\"detailFieldLabel\"\>Datierung\s*\<\/span\>\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>um (?P<date>\d\d\d\d)\s*(\(\?\))?\s*\<br\>\<\/span\>'
            periodregex = '\<span class\=\"detailFieldLabel\"\>Datierung\s*\<\/span\>\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)[-–\/](\d\d\d\d)\<br\>\<\/span\>'
            circaperiodregex = '\<span class\=\"detailFieldLabel\"\>Datierung\s*\<\/span\>\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>um\s*(\d\d\d\d)\/(\d\d\d\d)\<br\>\<\/span\>'
            otherdateregex = '\<span class\=\"detailFieldLabel\"\>Datierung\s*\<\/span\>\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>([^\<]+)\<br\>\<\/span\>'

            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            periodmatch = re.search(periodregex, itempage.text)
            circaperiodmatch = re.search(circaperiodregex, itempage.text)
            otherdatematch = re.search(otherdateregex, itempage.text)
            if datematch:
                # Don't worry about cleaning up here.
                metadata['inception'] = int(htmlparser.unescape(datematch.group(1).strip()))
            elif datecircamatch:
                metadata['inception'] = int(htmlparser.unescape(datecircamatch.group(1).strip()))
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1),)
                metadata['inceptionend'] = int(periodmatch.group(2),)
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print ('Could not parse date: "%s"' % (otherdatematch.group(1),))

            acquisitiondateregex = '\<span class\=\"detailFieldLabel\"\>Inventarzugang\s*\<\/span\>\<span class\=\"detailFieldValue\"\>(\d\d\d\d)([^\<]+)\<\/span\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)
                # Quite a few works seem to have been from the KHM
                if 'Übernahme aus dem Kunsthistorischen Museum' in acquisitiondatematch.group(2):
                    metadata['extracollectionqid'] = 'Q95569'

            mediumregex = '\<span class\=\"detailFieldLabel\"\>Material\/Technik\s*\<\/span\>\<span property\=\"artMedium\" itemprop\=\"artMedium\" class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>'
            mediummatch = match = re.search(mediumregex, itempage.text)
            if mediummatch:
                medium = mediummatch.group(1)
                # Not quite complete
                mediums = { 'Öl auf Leinwand' : 'oil on canvas',
                            'Öl auf Holz' : 'oil on panel',
                            'Öl auf Papier' : 'oil on paper',
                            'Öl auf Kupfer' : 'oil on copper',
                            'Tempera auf Leinwand' : 'tempera on canvas',
                            'Tempera auf Holz' : 'tempera on panel',
                            'Acryl auf Leinwand' : 'acrylic paint on canvas',
                            }
                if medium in mediums:
                    metadata['medium'] = mediums.get(medium)
                else:
                    print('Unable to match medium %s' % (medium,))

            measurementsregex = '\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Maße\s*\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>([^\<]+)\<\/div>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = '(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm'
                regex_3d = '(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group('height').replace(',', '.')
                    metadata['widthcm'] = match_2d.group('width').replace(',', '.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group('height').replace(',', '.')
                    metadata['widthcm'] = match_3d.group('width').replace(',', '.')
                    metadata['depthcm'] = match_3d.group('depth').replace(',', '.')

            imageidregex = '\<span\>Download\<\/span\>\<\/a\>\<div aria-labelledby\=\"downloadMediaLink\" class\=\"dropdown-menu\"\>\<a rel\=\"nofollow\" class\=\"dropdown-item\" href\=\"\/internal\/media\/downloaddispatcher\/(\d+)\;jsessionid\=[^\"]+\"\>'
            imageidmatch = re.search(imageidregex, itempage.text)
            if imageidmatch:
                metadata['imageurl'] = 'https://sammlung.belvedere.at/internal/media/downloaddispatcher/%s' % (imageidmatch.group(1),)
                metadata['imageurlformat'] = 'Q2195' #JPEG
                metadata['imageurllicense'] = 'Q18199165' # cc-by-sa-4.0 https://www.belvedere.at/en/open-content
                metadata['imageoperatedby'] = 'Q303139'
                # Could use this later to force
                metadata['imageurlforce'] = False


            # They insert a stupid Emuseum session id
            iiifregex = u'\<a class\=\"iiifLink\" href\=\"https\:\/\/digital\.belvedere\.at\/apis\/iiif\/presentation\/v2\/objects-(\d+)'
            iiifmatch = re.search(iiifregex, itempage.text)
            if iiifmatch:
                metadata['iiifmanifesturl'] = u'https://digital.belvedere.at/apis/iiif/presentation/v2/objects-%s/manifest' % (iiifmatch.group(1),)

            yield metadata


def main(*args):
    dictGen = getBelvedereGenerator()
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
