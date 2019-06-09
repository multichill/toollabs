#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Kunsthistorisches Museum in Vienna to Wikidata.

Just loop over pages like https://art.nationalgalleries.org/search?object_types[29864]=29864&page=0
Start at http://www.bellasartes.gob.ar/coleccion/objeto/pintura and use a session to retrieve the rest.

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getKHMGenerator():
    """
    Generator to return Kunsthistorisches Museum paintings
    """
    firsturl = u'https://www.khm.at/objektdb/?fq[facet_classification][]=Gem%C3%A4lde'
    #searchurl = u'https://www.khm.at/objektdb/?fq%5Bfacet_classification%5D%5B0%5D=Gem%C3%A4lde&cHash=f5cd712d07b7d8f2a5a63edad3389fd0&rand=0.22487490502052188&type=686&listOnly=1&page=203'
    basesearchurl = u'https://www.khm.at/objektdb/?fq%%5Bfacet_classification%%5D%%5B0%%5D=Gem%%C3%%A4lde&cHash=f5cd712d07b7d8f2a5a63edad3389fd0&rand=0.22487490502052188&type=686&listOnly=1&page=%s'
    htmlparser = HTMLParser.HTMLParser()

    session = requests.Session()

    for i in range(0, 206):
        searchurl = basesearchurl % (i,)

        print searchurl
        searchPage = session.get(searchurl, headers={'X-Requested-With' : 'XMLHttpRequest',
                                                     'referer' : firsturl,
                                                     })

        urls = []

        urlregex = u'href\=\"https?:\/\/(www\.khm\.at\/objektdb\/detail\/\d+\/)\?[^\"]+\"\>'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            # To remove duplicates, they mixed http and https. So annoying
            url = u'https://%s' % (match.group(1),)
            if url not in urls:
                urls.append(url)

        for url in urls:
            metadata = {}

            print url

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q95569'
            metadata['collectionshort'] = u'KHM'
            metadata['locationqid'] = u'Q95569'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            metadata['idpid'] = u'P217'

            invggregex = u'\<h2 class\=\"label\"\>Inv\. Nr\.\</\h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>Gemäldegalerie,\s*([^\<]*\d+[^\<]*)\<\/p\>\s*\<\/div\>'
            invsamregex = u'\<h2 class\=\"label\"\>Inv\. Nr\.\</\h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>Sammlung alter Musikinstrumente,\s*([^\<]*\d+[^\<]*)\<\/p\>\s*\<\/div\>'
            invwbregex = u'\<h2 class\=\"label\"\>Inv\. Nr\.\</\h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>Wagenburg,\s*([^\<]*\d+[^\<]*)\<\/p\>\s*\<\/div\>'
            invkkregex = u'\<h2 class\=\"label\"\>Inv\. Nr\.\</\h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>Kunstkammer,\s*([^\<]*\d+[^\<]*)\<\/p\>\s*\<\/div\>'
            invamregex = u'\<h2 class\=\"label\"\>Inv\. Nr\.\</\h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>Sammlungen Schloss Ambras,\s*([^\<]*\d+[^\<]*)\<\/p\>\s*\<\/div\>'
            invggmatch = re.search(invggregex, itempage.text)
            invsammatch = re.search(invsamregex, itempage.text)
            invwbmatch = re.search(invwbregex, itempage.text)
            invkkmatch = re.search(invkkregex, itempage.text)
            invammatch = re.search(invamregex, itempage.text)

            if invggmatch:
                metadata['id'] = 'GG_%s' % (invggmatch.group(1).strip(), )
            elif invsammatch:
                metadata['id'] = 'SAM_%s' % (invsammatch.group(1).strip(), )
            elif invwbmatch:
                metadata['id'] = 'WB_%s' % (invwbmatch.group(1).strip().replace(u' ', u'_'), )
            elif invkkmatch:
                metadata['id'] = 'KK_%s' % (invkkmatch.group(1).strip(), )
            elif invammatch:
                metadata['id'] = 'AM_%s' % (invammatch.group(1).strip().replace(u' ', u'_'), )
            else:
                pywikibot.output(u'Something went wrong, no inventory number found, skipping this one')
                continue

            # Sometimes the permalink forgets https
            permaregex = u'\<span class\=\"icon-permalink\"\>\<\/span\>\s*Permalink \(zitierbarer Link\) zu dieser Seite\: \<a target\=\"_top\" href\=\"https?\:\/\/(www\.khm\.at\/de\/object\/[^\"]+\/)\"\>'
            permamatch = re.search(permaregex, itempage.text)

            metadata['describedbyurl'] = u'https://%s' % (permamatch.group(1).strip(),)

            titleregex = u'\<meta property\=\"og:title\" content\=\"([^\"]+)\"\s*\/\>'
            titlematch = re.search(titleregex, itempage.text)
            title = htmlparser.unescape(titlematch.group(1).strip())
            #if not titlematch:
            #    pywikibot.output(u'No title match, something went wrong on %s' % (url,))
            #    continue
            ## Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'de' : title,
                                  }

            descriptionregex = u'\<meta property\=\"og:description\" content\=\"([^\"]+)\"\s*\/\>'
            descriptionmatch = re.search(descriptionregex, itempage.text)
            if not descriptionmatch:
                pywikibot.output(u'Something went wrong, no description found, skipping this one')
                continue
            (rawdate, sep, rawcreator) = htmlparser.unescape(descriptionmatch.group(1).strip()).replace(u', , Kunsthistorisches Museum Wien, Gemäldegalerie', u'').partition(u',')
            (creatortype, sep, name) = rawcreator.strip().partition(u':')
            # Don't use rawdate anymore

            if creatortype==u'Künstler':
                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                            u'en' : u'painting by %s' % (name, ),
                                            u'de' : u'Gemälde von %s' % (name, ),
                                            }
            else:
                # All sorts of anonymous works. Let's see if we can build decent descriptions
                metadata['creatorqid'] = u'Q4233718'
                if creatortype==u'Werkstatt':
                    metadata['description'] = { u'nl' : u'schilderij atelier van %s' % (name, ),
                                                u'en' : u'painting workshop of %s' % (name, ),
                                                u'de' : u'Gemälde Werkstatt von %s' % (name, ),
                                                }
                elif creatortype==u'Nach':
                    metadata['description'] = { u'nl' : u'schilderij naar %s' % (name, ),
                                                u'en' : u'painting after %s' % (name, ),
                                                u'de' : u'Gemälde Nach %s' % (name, ),
                                                }
                elif creatortype==u'Zugeschrieben an':
                    metadata['description'] = { u'nl' : u'schilderij toegeschreven aan %s' % (name, ),
                                                u'en' : u'painting attributed to %s' % (name, ),
                                                u'de' : u'Gemälde Zugeschrieben an %s' % (name, ),
                                                }
                else:
                    metadata['description'] = { u'de' : u'Gemälde %s %s' % (creatortype, name, ),
                                                }

            dateregex = u'\<h2 class\=\"label\"\>Datierung\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>(\d\d\d\d)\s*(datiert)?\<\/p\>'
            datecircaregex = u'\<h2 class\=\"label\"\>Datierung\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>\s*um\s*(\d\d\d\d)\s*\<\/p\>'
            periodregex = u'\<h2 class\=\"label\"\>Datierung\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>\s*zwischen\s*(\d\d\d\d)\s*-\s*(\d\d\d\d)\s*\<\/p\>'
            circaperiodregex = u'\<h2 class\=\"label\"\>Datierung\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>\s*um\s*(\d\d\d\d)\s*\/\s*(\d\d\d\d)\s*\<\/p\>'
            circashortperiodregex = u'\<h2 class\=\"label\"\>Datierung\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>\s*um\s*(\d\d)(\d\d)\s*\/\s*(\d\d)\s*\<\/p\>'
            otherdateregex = u'\<h2 class\=\"label\"\>Datierung\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>([^\<]+)\<\/p\>'
            datematch = re.search(dateregex, itempage.text)
            datecircamatch = re.search(datecircaregex, itempage.text)
            periodmatch = re.search(periodregex, itempage.text)
            circaperiodmatch = re.search(circaperiodregex, itempage.text)
            circashortperiodmatch = re.search(circashortperiodregex, itempage.text)
            otherdatematch = re.search(otherdateregex, itempage.text)
            if datematch:
                metadata['inception'] = htmlparser.unescape(datematch.group(1).strip())
            elif datecircamatch:
                metadata['inception'] = htmlparser.unescape(datecircamatch.group(1).strip())
                metadata['inceptioncirca'] = True
            elif periodmatch:
                metadata['inceptionstart'] = int(periodmatch.group(1),)
                metadata['inceptionend'] = int(periodmatch.group(2),)
            elif circaperiodmatch:
                metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                metadata['inceptioncirca'] = True
            elif circashortperiodmatch:
                metadata['inceptionstart'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(2),))
                metadata['inceptionend'] = int(u'%s%s' % (circashortperiodmatch.group(1),circashortperiodmatch.group(3),))
                metadata['inceptioncirca'] = True
            elif otherdatematch:
                print (u'Could not parse date: "%s"' % (otherdatematch.group(1),))

            # No data
            # metadata['acquisitiondate'] = acquisitiondatematch.group(1)
            #  metadata['medium'] = u'oil on canvas'

            measurementsregex = u'\<h2 class\=\"label\"\>Maße\<\/h2\>\s*\<\/div\>\s*\<div class\=\"medium-8 columns\"\>\s*\<p\>([^\<]+)\<\/p\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                measurementstext = measurementsmatch.group(1)
                regex_2d = u'(?P<height>\d+(,\d+)?) x (?P<width>\d+(,\d+)?) cm.*'
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

            yield metadata

def main():
    dictGen = getKHMGenerator()

    #for painting in dictGen:
    #    print (painting)

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
