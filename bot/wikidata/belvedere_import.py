#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the  Österreichische Galerie Belvedere in Vienna to Wikidata.

Just loop over pages like http://digital.belvedere.at/advancedsearch/objects/name:Gemälde/images?page=1

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getBelvedereGenerator():
    """
    Generator to return Belvedere paintings
    """
    #basesearchurl = u'http://digital.belvedere.at/advancedsearch/objects/name:Gemälde/images?page=%s'
    # This one is for all the paintings
    basesearchurl = u'https://digital.belvedere.at/advancedsearch/Objects/classifications%%3AMalerei/images?page=%s'
    # Leftovers
    #basesearchurl = u'https://digital.belvedere.at/advancedsearch/Objects/name%%3ATafelbild/images?page=%s'
    htmlparser = HTMLParser.HTMLParser()

    for i in range(1, 341): #12): # 341):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        urlregex = u'data-a2a-url\=\"(https?:\/\/digital\.belvedere\.at\/objects\/(\d+)\/[^\"]+)\;jsessionid\=[^\"]+\"'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = match.group(1)

            metadata['artworkidpid'] = u'P5823'
            metadata['artworkid'] = match.group(2)

            # Museum site doesn't seem to like it when we go fast
            time.sleep(15)

            pywikibot.output(url)
            try:
                itempage = requests.get(url)
            except requests.exceptions.ConnectionError:
                time.sleep(60)
                itempage = requests.get(url)

            metadata['url'] = url
            metadata['collectionqid'] = u'Q303139'
            metadata['collectionshort'] = u'Belvedere'
            metadata['locationqid'] = u'Q303139'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'
            invregex = u'\<div class\=\"detailField invnoField\"\>\<span class\=\"detailFieldLabel\"\>Inventarnummer:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>([^\<]+)\<\/span\>\<\/div\>'
            invmatch = re.search(invregex, itempage.text)
            if invmatch:
                metadata['id'] = invmatch.group(1).strip()
            else:
                pywikibot.output(u'Something went wrong, no inventory number found, skipping this one')
                continue

            titleregex = u'\<div class\=\"detailField titleField\"\>\<h2 property\=\"name\" itemprop\=\"name\"\>([^\<]+)\<\/h2\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1).strip())
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'de' : title,
                                  }
            # This one is not complete, attributed works will be missed
            # creatorregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema:creator\" itemprop\=\"creator\"\>'
            creatorregex = u'\<span class\=\"detailFieldLabel\"\>Künstler\/in\:\s*\<\/span\>\<span typeof\=\"schema\:Person\" itemtype\=\"\/\/schema\.org\/Person\" itemscope\=\"\" class\=\"detailFieldValue\"\>\<a property\=\"url\" itemprop\=\"url\" href\=\"\/people\/\d+\/[^\"]+\"\>\<span property\=\"name\" itemprop\=\"name\"\>[\r\n\t\s]*([^\<]+)[\r\n\t\s]*\<\/span\>'
            creatormatch = re.search(creatorregex, itempage.text)
            if creatormatch:
                name = htmlparser.unescape(creatormatch.group(1).strip())

                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                            u'en' : u'painting by %s' % (name, ),
                                            u'de' : u'Gemälde von %s' % (name, ),
                                            }
            else:
                metadata['creatorname'] = u'anonymous'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                        }
                metadata['creatorqid'] = u'Q4233718'


            # Was broken too
            #dateregex = u'\<meta content\=\"([^\"]+)\" property\=\"schema:dateCreated\" itemprop\=\"dateCreated\"\>'
            dateregex = u'\<span class\=\"detailFieldLabel\"\>Datierung\: \<\/span\>\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>(\d\d\d\d)\<\/span\>'
            datematch = re.search(dateregex, itempage.text)
            if datematch:
                # Don't worry about cleaning up here.
                metadata['inception'] = htmlparser.unescape(datematch.group(1).strip())
            else:
                datecircaregex = u'\<span class\=\"detailFieldLabel\"\>Datierung\: \<\/span\>\<span property\=\"dateCreated\" itemprop\=\"dateCreated\" class\=\"detailFieldValue\"\>um (\d\d\d\d)\<\/span\>'
                datecircamatch = re.search(datecircaregex, itempage.text)
                if datecircamatch:
                    metadata['inception'] = htmlparser.unescape(datecircamatch.group(1).strip())
                    metadata['inceptioncirca'] = True

            # Probably too

            acquisitiondateregex = u'\<span class\=\"detailFieldLabel\"\>Inventarzugang:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>(\d\d\d\d)([^\<]+)\<\/span\>'
            acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = acquisitiondatematch.group(1)
                # Quite a few works seem to have been from the KHM
                if u'Übernahme aus dem Kunsthistorischen Museum' in acquisitiondatematch.group(2):
                    metadata['extracollectionqid'] = u'Q95569'

            #mediumregex = u'\<meta content\=\"Öl auf Leinwand\" property\=\"schema:artMedium\" itemprop\=\"artMedium\"\>'
            mediumregex = u'\<span class\=\"detailFieldLabel\"\>Material\/Technik\: \<\/span\>\<span property\=\"artMedium\" itemprop\=\"artMedium\" class\=\"detailFieldValue\"\>Öl auf Leinwand\<\/span\>'
            mediummatch = match = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<div class\=\"detailField dimensionsField\"\>\<span class\=\"detailFieldLabel\"\>Maße:\s*\<\/span\>\<span class\=\"detailFieldValue\"\>\<div\>([^\<]+)\<\/div>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm'
                regex_3d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) x (?P<depth>\d+(,\d+)?) cm.*'
                match_2d = re.match(regex_2d, measurementstext)
                match_3d = re.match(regex_3d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_2d.group(u'width').replace(u',', u'.')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height').replace(u',', u'.')
                    metadata['widthcm'] = match_3d.group(u'width').replace(u',', u'.')
                    metadata['depthcm'] = match_3d.group(u'depth').replace(u',', u'.')

            imageidregex = u'\<div class\=\"media-download-content\"\>\<ul\>\<li\>\<a href\=\"\/objects\/details\.detail\.mediaoverlay\.primarymediaoverlay\.downloadbuttonprivate\/(\d+)'
            imageidmatch = re.search(imageidregex, itempage.text)
            if imageidmatch:
                metadata[u'imageurl'] = u'https://digital.belvedere.at/internal/media/downloaddispatcher/%s' % (imageidmatch.group(1),)
                metadata[u'imageurlformat'] = u'Q2195' #JPEG
                metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa-4.0
                # Could use this later to force
                metadata[u'imageurlforce'] = False

            # They insert a stupid Emuseum session id
            iiifregex = u'\<a class\=\"iiifLink\" href\=\"https\:\/\/digital\.belvedere\.at\/apis\/iiif\/presentation\/v2\/objects-(\d+)'
            iiifmatch = re.search(iiifregex, itempage.text)
            if iiifmatch:
                metadata['iiifmanifesturl'] = u'https://digital.belvedere.at/apis/iiif/presentation/v2/objects-%s/manifest' % (iiifmatch.group(1),)

            yield metadata


def main():
    dictGen = getBelvedereGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
