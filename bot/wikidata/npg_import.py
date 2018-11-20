#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the National Portrait Gallery in London to Wikidata.

Just loop over pages like www.npg.org.uk/collections/search/portrait-list.php?search=ap&firstRun=true&medium=painting&wPage=0

This bot does use artdatabot to upload it to Wikidata and just asks the API for all it's paintings.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getNPGGenerator():
    """
    Generator to return Museum of Fine Arts, Houston paintings
    """
    basesearchurl = u'http://www.npg.org.uk/collections/search/portrait-list.php?search=ap&firstRun=true&medium=painting&displayNo=60&wPage=%s'
    htmlparser = HTMLParser.HTMLParser()

    # Keep track of the failed pages
    failedurls = []

    # 3141 results, 60 per page
    for i in range(0, 53):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        #urlregex = u'\<a href\=\"(\/art\/detail\/\d+)\?returnUrl\=[^\"]+\"\>[^\<]+\<\/a\>'
        urlregex = u'\<a href\=\"(\/collections\/search\/portrait\/mw\d+\/[^\?]+)\?search=ap[^\"]+\"\>[^\<]+\<\/a\>'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = u'http://www.npg.org.uk%s' % (match.group(1),)

            # Museum site probably doesn't like it when we go fast
            time.sleep(5)

            pywikibot.output(url)

            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q238587'
            metadata['collectionshort'] = u'NPG'
            metadata['locationqid'] = u'Q238587'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            bigregex = u'\<p class\=\'title\'\>(?P<title>[^\<]+)\<\/p\>\<p\>(?P<creator>[^\<]+)\<br \/\>(?P<medium>[^,\<]+)(?P<date>, [^\<]+)?\<br \/\>(?P<measurements>[^\<]+)\<br \/\>((?P<creditline>[^\<]+)\<br \/\>)?\<a href\=\"\.\.\/primcoll\.asp\"\>Primary Collection\<\/a\>\<br \/\>(?P<id>NPG [^\<]+)\<\/p\>'
            bigmatch = re.search(bigregex, itempage.text)

            if not bigmatch:
                pywikibot.output(u'Bigregex failed, skipping')
                failedurls.append(url)
                continue

            metadata['idpid'] = u'P217'
            metadata['id'] = bigmatch.group('id').strip()

            #else:
            #    pywikibot.output(u'Something went wrong, no inventory number found, skipping this one')
            #    continue

            title = htmlparser.unescape(bigmatch.group('title').strip())

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { u'en' : title,
                                  }
            name = htmlparser.unescape(bigmatch.group('creator').strip())
            if name==u'by Unknown artist':
                metadata['creatorname'] = u'unknown artist'
                metadata['description'] = { u'nl' : u'schilderij van anonieme schilder',
                                            u'en' : u'painting by anonymous painter',
                                            }
                metadata['creatorqid'] = u'Q4233718'
            elif name.startswith(u'by '):
                name = name[3:]
                metadata['creatorname'] = name
                metadata['description'] = { u'nl' : u'schilderij van %s' % (name, ),
                                            u'en' : u'painting by %s' % (name, ),
                                        }
            else:
                metadata['creatorname'] = name
                metadata['description'] = { u'en' : u'painting %s' % (name, ),
                                            }
                metadata['creatorqid'] = u'Q4233718'

            dateregex = u'^, (\d\d\d\d)$'
            if bigmatch.group('date'):
                datematch = re.match(dateregex, bigmatch.group('date'))
                if datematch:
                    metadata['inception'] = datematch.group(1)

            acquisitiondateregex = u'^.+(\d\d\d\d)$'
            if bigmatch.group('creditline'):
                acquisitiondatematch = re.match(acquisitiondateregex, bigmatch.group('creditline'))
                if acquisitiondatematch:
                    metadata['acquisitiondate'] = acquisitiondatematch.group(1)

            if bigmatch.group('medium')==u'oil on canvas':
                metadata['medium'] = u'oil on canvas'


            if bigmatch.group('measurements'):
                measurementstext = bigmatch.group('measurements')
                regex_2d = u'^.+ \((?P<height>\d+) mm x (?P<width>\d+) mm\)$'
                match_2d = re.match(regex_2d, measurementstext)
                if match_2d:
                    metadata['heightcm'] = unicode(float(match_2d.group(u'height'))/10)
                    metadata['widthcm'] = unicode(float(match_2d.group(u'width'))/10)

            yield metadata
    pywikibot.output(u'The list of %s failed urls:' % (len(failedurls),))
    pywikibot.output(failedurls)


def main():
    dictGen = getNPGGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
