#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Barnes Foundation (Q808462) to Wikidata.

Just loop over pages like http://www.barnesfoundation.org/collections/art-collection/collection-search?classID=19&submit=submit&page=43

This bot does use artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
import HTMLParser

def getBarnesGenerator():
    """
    Generator to return Barnes Foundation paintings
    """
    basesearchurl = u'https://www.barnesfoundation.org/collections/art-collection/collection-search?classID=19&submit=submit&page=%s'
    htmlparser = HTMLParser.HTMLParser()

    # 963 results, 20 per page (starting at 0)
    for i in range(0, 49):
        searchurl = basesearchurl % (i,)

        pywikibot.output(searchurl)
        searchPage = requests.get(searchurl)

        urlregex = u'\<a class\=\"collections-result\" href\=\"(\/collections\/art-collection\/object\/[^\?]+)\?[^\"]+\"\>'
        matches = re.finditer(urlregex, searchPage.text)
        for match in matches:
            metadata = {}
            url = u'https://www.barnesfoundation.org%s' % (match.group(1),)

            # Museum site probably doesn't like it when we go fast
            # time.sleep(5)

            pywikibot.output(url)


            itempage = requests.get(url)
            metadata['url'] = url

            metadata['collectionqid'] = u'Q808462'
            metadata['collectionshort'] = u'Barnes'
            metadata['locationqid'] = u'Q808462'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = u'Q3305213'

            # Data is structured in an akward way. First the painter, than an info block without much structure

            creatorregex = u'\<h2 class\=\'artist\'\>(?P<anonymous>[^\<]+)?(\<a href\=\'[^\']+\'\s*\>(?P<name>[^\<]+)\<\/a\>)?\<\/h2\>'
            creatormatch = re.search(creatorregex, itempage.text)

            if not creatormatch.group(u'name'):
                metadata['creatorqid'] = u'Q4233718'
                metadata['description'] = { u'en' : u'painting by anonymous painter',
                                            u'nl' : u'schilderij van anonieme schilder',
                                            }
            else:
                name = htmlparser.unescape(creatormatch.group(u'name').strip())
                if creatormatch.group(u'anonymous'):
                    anonymous = htmlparser.unescape(creatormatch.group(u'anonymous').strip())
                    metadata['creatorqid'] = u'Q4233718'
                    metadata['description'] = { u'en' : u'painting %s %s' % (anonymous, name,),
                                                }
                else:
                    metadata['creatorname'] = name
                    metadata['description'] = { u'en' : u'painting by %s' % (name, ),
                                                u'nl' : u'schilderij van %s' % (name, ),
                                                }

            # Fix inventory numbers like 2001.25.50a,b,c
            bigregex = u'\<div class\=\'info-block\'\>(\<h1 class\=\'obj-title\'\>(?P<title>[^\<]+)\<\/h1\>)?(\<span\>(?P<date>[^\<]+)\<\/span\>)?(\<span\>(?P<medium>[^\<]+)\<\/span\>)?(\<span\>(?P<dimensions>[^\<]+in[^\<]+cm[^\<]+)\<\/span\>)?\<span\>(?P<id>(BF[^\<]+|2001\.[^\<]+))\<\/span\>\<\/div\>'
            bigmatch = re.search(bigregex, itempage.text)

            #print u'Title: %s ' % (bigmatch.group(u'title'),)
            #print u'date: %s ' % (bigmatch.group(u'date'),)
            #print u'medium: %s ' % (bigmatch.group(u'medium'),)
            #print u'dimensions: %s ' % (bigmatch.group(u'dimensions'),)
            #print u'id: %s ' % (bigmatch.group(u'id'),)

            # If no id is found the bot will crash here
            metadata['idpid'] = u'P217'
            metadata['id'] = bigmatch.group(u'id').strip()

            if bigmatch.group(u'title'):
                title = htmlparser.unescape(bigmatch.group(u'title').strip())
                # Chop chop, in case we have very long titles
                if title > 220:
                    title = title[0:200]
                metadata['title'] = { u'en' : title,
                                    }

            # Small chance that this contains something weird. Artdata bot checks before adding so that should be enough
            if bigmatch.group(u'date'):
                metadata['inception'] = htmlparser.unescape(bigmatch.group(u'date').strip())
            if bigmatch.group(u'medium') and bigmatch.group(u'medium').strip()==u'Oil on canvas':
                metadata['medium'] = u'oil on canvas'
            if bigmatch.group(u'dimensions'):
                dimensiontext = bigmatch.group(u'dimensions').strip()
                regex_2d = u'.+\((?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) cm\)$'
                regex_3d = u'.+\((?P<height>\d+(\.\d+)?) x (?P<width>\d+(\.\d+)?) x (?P<depth>\d+(\.\d+)?) cm\)$'
                match_2d = re.match(regex_2d, dimensiontext)
                match_3d = re.match(regex_3d, dimensiontext)
                if match_2d:
                    metadata['heightcm'] = match_2d.group(u'height')
                    metadata['widthcm'] = match_2d.group(u'width')
                elif match_3d:
                    metadata['heightcm'] = match_3d.group(u'height')
                    metadata['widthcm'] = match_3d.group(u'width')
                    metadata['depthcm'] = match_3d.group(u'depth')

            yield metadata


def main():
    dictGen = getBarnesGenerator()

    #for painting in dictGen:
    #    print painting

    artDataBot = artdatabot.ArtDataBot(dictGen, create=True)
    artDataBot.run()

if __name__ == "__main__":
    main()
