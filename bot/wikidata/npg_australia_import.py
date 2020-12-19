#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the National Portrait Gallery (Australia) to Wikidata.

Just loop over pages like https://www.portrait.gov.au/portraits.php?direction=1&advanced=yes&startat=13&display=images&query=&sa=all&l=&sort=acquired&ey=&sy=&by=-1&m=Paintings&i=both&s=&ss=&g=&e=&sagsy=&sagey=&ae=&agn=&aagsy=&aagsey=&p=-1&pt=&d=-1&ay=&f=-1&cp=&cu=&r=&ch=&sc=

This bot does uses artdatabot to upload it to Wikidata.

"""
import artdatabot
import pywikibot
import requests
import re
import time
from html.parser import HTMLParser

def getNPGAGenerator():
    """
    Generator to return NPG Australia paintings
    """
    basesearchurl = 'https://www.portrait.gov.au/portraits.php?direction=1&advanced=yes&startat=%s&display=images&query=&sa=all&l=&sort=acquired&ey=&sy=&by=-1&m=Paintings&i=both&s=&ss=&g=&e=&sagsy=&sagey=&ae=&agn=&aagsy=&aagsey=&p=-1&pt=&d=-1&ay=&f=-1&cp=&cu=&r=&ch=&sc='
    htmlparser = HTMLParser()

    session = requests.Session()
    persons = npgPersonsOnWikidata()

    # 536 hits, 12 per page.
    for i in range(37, 552, 12):
        searchurl = basesearchurl % (i,)

        print (searchurl)
        searchPage = session.get(searchurl)

        workurlregex = '\<a href\=\"\/portraits\/([^\"]+)\/([^\"]+)\" class\=\"portrait\"'
        matches = re.finditer(workurlregex, searchPage.text)

        for match in matches:
            metadata = {}
            invnumber = match.group(1)
            slug = match.group(2) # Can be anything
            url = 'https://www.portrait.gov.au/portraits/%s/%s' % (invnumber, slug)

            itempage = session.get(url)
            pywikibot.output(url)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q1489633'
            metadata['collectionshort'] = 'NPG'
            metadata['locationqid'] = 'Q1489633'

            #No need to check, I'm actually searching for paintings.
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'
            metadata['id'] = invnumber

            titlelinknameregex = '\<h1\s*\>([^\<]+)\<\/h1\>[\r\n\s\t]*\<h2\s*\>[\r\n\s\t]*<span style\=\"white-space\:nowrap;\"\>\<a href\=\"\/people\/([^\"]+)\"\>([^\<]+)\<\/a\>\<\/span\>'
            titlenameregex = '\<h1\s*\>([^\<]+)\<\/h1\>[\r\n\s\t]*\<h2\s*\>[\r\n\s\t]*<span style\=\"white-space\:nowrap;\"\>([^\<]+)\<\/span\>'
            titleregex = '\<h1\s*\>([^\<]+)\<\/h1\>[\r\n\s\t]*\<h2\s*\>'

            titlenlinkamematch = re.search(titlelinknameregex, itempage.text)
            titlenamematch = re.search(titlenameregex, itempage.text)
            titlematch = re.search(titleregex, itempage.text)

            if titlenlinkamematch:
                title = htmlparser.unescape(titlenlinkamematch.group(1)).strip()
                peopleid = htmlparser.unescape(titlenlinkamematch.group(2)).strip()
                creatorname = htmlparser.unescape(titlenlinkamematch.group(3)).strip()
            elif titlenamematch:
                title = htmlparser.unescape(titlenamematch.group(1)).strip()
                peopleid = None
                creatorname = htmlparser.unescape(titlenamematch.group(2)).strip()
            else:
                # Bot should crash if the other regex doesn't match either
                title = htmlparser.unescape(titlematch.group(1)).strip()
                peopleid = None
                creatorname = ''

            titledateregex = '(.+),\s*(\d\d\d\d)'
            titledatecircaregex = '(.+),\s*ca?\.\s*(\d\d\d\d)'

            titledatematch = re.search(titledateregex, title)
            titledatecircamatch = re.search(titledatecircaregex, title)

            if titledatematch:
                title = titledatematch.group(1)
                metadata['inception'] = int(titledatematch.group(2).strip())
            elif titledatecircamatch:
                title = titledatecircamatch.group(1)
                metadata['inception'] = int(titledatecircamatch.group(2).strip())
                metadata['inceptioncirca'] = True
            else:
                print ('Could not get date from title: "%s"' % (title,))
            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            metadata['title'] = { 'en' : title,
                                  }
            if creatorname:
                metadata['creatorname'] = creatorname
                metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                            'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                            'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                            'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                            }

            if peopleid:
                if peopleid in persons:
                    pywikibot.output ('Found NPG Australia person id %s on %s' % (peopleid, persons.get(peopleid)))
                    metadata['creatorqid'] = persons.get(peopleid)


            ## The inventory number starts with the year.
            acquisitiondateregex = '(\d\d\d\d)\.\d+'
            acquisitiondatematch = re.search(acquisitiondateregex, invnumber)
            if acquisitiondatematch:
                metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            mediumregex = '\<div class\=\"portraitdetails\"\>[\r\n\s\t]*oil on canvas'
            mediummatch = re.search(mediumregex, itempage.text)
            if mediummatch:
                metadata['medium'] = 'oil on canvas'

            # Dimensions are for the frame and the support. I want the support
            measurementsregex = '\>support\:\s*\<span title\=\"height\"\>(?P<height>\d+(\.\d+)?)\s*cm\<\/span\>\s*x\s*\<span title\=\"width\"\>(?P<width>\d+(\.\d+)?)\s*cm\<\/span\>'
            measurementsmatch = re.search(measurementsregex, itempage.text)
            if measurementsmatch:
                metadata['heightcm'] = measurementsmatch.group('height').replace(',', '.')
                metadata['widthcm'] = measurementsmatch.group('width').replace(',', '.')

            # No free images
            #imageregex = '\<div style\=\"[^\"]+\" class\=\"emuseum-img-wrap width-img-wrap\" data-mediatype-id\=\"\d*\"\>\<img src\=\"(\/internal\/media\/dispatcher\/\d+\/unrestricted)\"'
            #imagematch = re.search(imageregex, itempage.text, re.IGNORECASE)
            #if imagematch:
            #    recentinception = False
            #    if metadata.get('inception') and metadata.get('inception') > 1924:
            #        recentinception = True
            #    if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
            #        recentinception = True
            #    if not recentinception:
            #        metadata['imageurl'] = 'https://collection.crystalbridges.org%s' % (imagematch.group(1),)
            #        metadata['imageurlformat'] = 'Q2195' #JPEG
            #        #metadata[u'imageurllicense'] = u'Q18199165' # cc-by-sa.40
            #        metadata['imageoperatedby'] = 'Q1142334'
            #        #Used this to add suggestions everywhere
            #        metadata[u'imageurlforce'] = True

            yield metadata

def npgPersonsOnWikidata():
    """
    Just return all the NPG Australia persons as a dict
    :return: Dict
    """
    return [] # Have to actually get the property created
    result = {}
    query = 'SELECT ?item ?id WHERE { ?item wdt:P<create me> ?id . ?item wdt:P31 wd:Q5 }'
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        qid = resultitem.get('item').replace('http://www.wikidata.org/entity/', '')
        result[resultitem.get('id')] = qid
    return result

def main(*args):
    dictGen = getNPGAGenerator()
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
