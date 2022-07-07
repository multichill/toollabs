#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Musée des Beaux-Arts de Quimper to Wikidata.

Just loop over pages https://collections.mbaq.fr/fr/search-notice?q=&only_img=0&type=list&filters%5Bfacets.id%5D%5B0%5D=5a2e83704e1f6e1ff48b4573&page=2

This bot uses artdatabot to upload it to Wikidata. Site was acting up so I had to do some hacks

"""
import artdatabot
import pywikibot
import requests
import re
import html
import time
import random
import pywikibot.data.sparql

def urls_on_wikidata():
    """
    Get the list of urls of paintings already uploaded to Wikidata
    :return:
    """
    result = []
    query = """SELECT DISTINCT ?item ?url WHERE {
  ?item p:P195/ps:P195 wd:Q3330220 ;
        p:P217/pq:P195 wd:Q3330220 ;
        wdt:P31 wd:Q3305213 ;
        wdt:P973 ?url  .
}
LIMIT 4000"""
    sq = pywikibot.data.sparql.SparqlQuery()
    queryresult = sq.select(query)

    for resultitem in queryresult:
        url = resultitem.get('url')
        result.append(url)

    return result


def get_mbaq_generator():
    """
    Generator to return New Britain Museum of American Art paintings
    """
    base_search_url = 'https://collections.mbaq.fr/fr/search-notice?q=&only_img=0&type=list&filters%%5Bfacets.id%%5D%%5B0%%5D=5a2e83704e1f6e1ff48b4573&page=%s'
    # TODO: I could also add the watercolour paintings
    ## Not sure if this needed for thie Emuseum instance
    headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0' }
    session = requests.Session()
    session.headers.update(headers)
    #session.get('https://ink.nbmaa.org/collections')

    mediums = { 'huile sur toile' : 'oil on canvas',
                'huile sur bois' : 'oil on panel',
                }
    urls = urls_on_wikidata()



    int_range = list(range(1, 52))

    #int_range = [8, 9, 10,
    #        13, 17, 18, 20,
    #        21, 25, 26, 28,
    #        35, 37, 38, 40,
    #        41, 44, 45,
    #        ]

    random.shuffle(int_range)
    for i in int_range:
        search_url = base_search_url % (i,)

        print (search_url)
        search_page = session.get(search_url)

        work_url_regex = '<a href=\"(/fr/search-notice/detail/[^\"]+)\"'
        matches = re.finditer(work_url_regex, search_page.text)
        if not matches:
            time.sleep(600)

        for match in matches:
            metadata = {}
            #title = html.unescape(match.group(1)).strip()
            url = 'https://collections.mbaq.fr%s' % (match.group(1),)

            if url in urls:
                print('Already worked on %s, skipping' % (url,))
                continue

            #version = random.randrange(10, 99)
            #headers = { 'User-Agent' : 'Mozilla/5.0 (X11; UbuntuX; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/%s.0' % (version)}
            #session.headers.update(headers)

            #pywikibot.output ('Backing up this url to the Wayback Machine: %s' % (url,))
            #waybackUrl = u'https://web.archive.org/save/%s' % (url,)
            #try:
            #    waybackPage = requests.post(waybackUrl)
            #except requests.exceptions.RequestException:
            #    pywikibot.output('Requests threw an exception. The wayback backup failed')
            #    pass

            waybackurl = 'https://web.archive.org/web/%s' % (url,)

            itempage = session.get(url)
            pywikibot.output(waybackurl)
            metadata['url'] = url

            metadata['collectionqid'] = 'Q3330220'
            metadata['collectionshort'] = 'MBAQ'
            metadata['locationqid'] = 'Q3330220'

            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'

            inv_regex = '<h3>Numéro d&#039;inventaire :</h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span>'
            inv2_regex = '<h3>Numéro de dépôt :</h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span>'
            inv_match = re.search(inv_regex, itempage.text)
            inv2_match = re.search(inv2_regex, itempage.text)

            if inv_match:
                metadata['id'] = html.unescape(inv_match.group(1).replace('&nbsp;', ' ')).strip()
            elif inv2_match:
                metadata['id'] = html.unescape(inv2_match.group(1).replace('&nbsp;', ' ')).strip()
            else:
                # Getting some blank pages
                print('Got blank page, sleeping and skipping')
                time.sleep(60)
                continue
                #session = requests.Session()
                #itempage = session.get(url)
                #inv_match = re.search(inv_regex, itempage.text)

            title_regex = '<h3><strong>Titre de l\'&oelig;uvre</strong></h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span>'
            title_match = re.search(title_regex, itempage.text)
            title = html.unescape(title_match.group(1)).strip()

            # Chop chop, several very long titles
            if len(title) > 220:
                title = title[0:200]
            #title = title.replace('\t', '').replace('\n', '')
            metadata['title'] = {'fr': title, }

            creator_role_name_regex = '<h3>Rôle de l&#039;auteur :</h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span><span class="separator">;</span><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span><h3>Auteur :</h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span>'
            creator_role_name_match = re.search(creator_role_name_regex, itempage.text)

            creator_name_regex = '<h3>Rôle de l&#039;auteur :</h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span><h3>Auteur :</h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span>'
            creator_name_match = re.search(creator_name_regex, itempage.text)

            uncertain_creator = True
            creator_role = None
            creator_name = ''

            if creator_role_name_match:
                creation = html.unescape(creator_role_name_match.group(1)).strip()
                creator_role = html.unescape(creator_role_name_match.group(2)).strip()
                creator_name = html.unescape(creator_role_name_match.group(3)).strip()
                if creation == 'Création' and creator_role == 'Auteur':
                    uncertain_creator = False
            elif creator_name_match:
                creation = html.unescape(creator_name_match.group(1)).strip()
                creator_name = html.unescape(creator_name_match.group(2)).strip()
                if creation == 'Création':
                    uncertain_creator = False

            if creator_name:
                surname_regex = '^([A-Z\-\s]+) (.+)$'
                surname_match = re.match(surname_regex, creator_name)
                if surname_match:
                    creator_name = '%s %s' % (surname_match.group(2), surname_match.group(1).capitalize())
                metadata['creatorname'] = creator_name

                if uncertain_creator and creator_role:
                    metadata['description'] = {'fr' : 'painture %s %s' % (creator_role, metadata.get('creatorname'), ),}
                elif not uncertain_creator:
                    metadata['description'] = { 'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'), ),
                                                'fr' : '%s de %s' % ('peinture', metadata.get('creatorname'), ),
                                                }

            date_regex = '<h3>Date de création :</h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span>'
            date_match = re.search(date_regex, itempage.text)
            if date_match:
                date = html.unescape(date_match.group(1)).strip()
                year_regex = '^(\d\d\d\d)$'
                date_circa_regex = '^ca?\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)[--\/](\d\d\d\d)$'
                circa_period_regex = '^ca?\.\s*(\d\d\d\d)–(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[--\/](\d\d)$'
                circa_short_period_regex = '^ca?\.\s*(\d\d)(\d\d)[-–/](\d\d)$'

                year_match = re.match(year_regex, date)
                date_circa_match = re.match(date_circa_regex, date)
                period_match = re.match(period_regex, date)
                circa_period_match = re.match(circa_period_regex, date)
                short_period_match = re.match(short_period_regex, date)
                circa_short_period_match = re.match(circa_short_period_regex, date)

                if year_match:
                    # Don't worry about cleaning up here.
                    metadata['inception'] = int(year_match.group(1))
                elif date_circa_match:
                    metadata['inception'] = int(date_circa_match.group(1))
                    metadata['inceptioncirca'] = True
                elif period_match:
                    metadata['inceptionstart'] = int(period_match.group(1),)
                    metadata['inceptionend'] = int(period_match.group(2),)
                elif circa_period_match:
                    metadata['inceptionstart'] = int(circa_period_match.group(1),)
                    metadata['inceptionend'] = int(circa_period_match.group(2),)
                    metadata['inceptioncirca'] = True
                elif short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(2), ))
                    metadata['inceptionend'] = int('%s%s' % (short_period_match.group(1), short_period_match.group(3), ))
                elif circa_short_period_match:
                    metadata['inceptionstart'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(2), ))
                    metadata['inceptionend'] = int('%s%s' % (circa_short_period_match.group(1), circa_short_period_match.group(3), ))
                    metadata['inceptioncirca'] = True
                else:
                    print('Could not parse date: "%s"' % (date,))

            medium_regex = '<h3><strong>Matière et technique</strong></h3><span>[\s\t\r\n]*([^<]+)[\s\t\r\n]*</span>'
            medium_match = re.search(medium_regex, itempage.text)
            # Artdatabot will sort this out
            if medium_match:
                medium = html.unescape(medium_match.group(1)).strip().lower()
                if medium in mediums:
                    metadata['medium'] = mediums.get(medium)
                else:
                    metadata['medium'] = medium

            yield metadata
            time.sleep(30)
            continue

            # TODO: Implement rest

            dimensions_regex = '<div class="detailField dimensionsField"><span class="detailFieldLabel">Dimensions</span><span class="detailFieldValue">[^\(]+\(([^\)]+ cm)\)</span>'
            dimensions_match = re.search(dimensions_regex, itempage.text)

            if dimensions_match:
                dimensions = dimensions_match.group(1)
                regex_2d = '\s*(?P<height>\d+(\.\d+)?)\s*×\s*(?P<width>\d+(\.\d+)?)\s*cm\s*$'
                match_2d = re.match(regex_2d, dimensions)
                if match_2d:
                    metadata['heightcm'] = match_2d.group('height')
                    metadata['widthcm'] = match_2d.group(u'width')

            ### Nothing useful here, might be part of the inventory number
            #acquisitiondateregex = '\<div class\=\"detailField creditlineField\"\>[^\<]+,\s*(\d\d\d\d)\<\/div\>'
            #acquisitiondatematch = re.search(acquisitiondateregex, itempage.text)
            #if acquisitiondatematch:
            #    metadata['acquisitiondate'] = int(acquisitiondatematch.group(1))

            # Image url is provided and it's a US collection. Just check the date
            image_regex = '<meta content="(https://ink\.nbmaa\.org/internal/media/dispatcher/\d+/full)" name="og:image">'
            image_match = re.search(image_regex, itempage.text)
            if image_match:
                recent_inception = False
                if metadata.get('inception') and metadata.get('inception') > 1924:
                    recent_inception = True
                if metadata.get('inceptionend') and metadata.get('inceptionend') > 1924:
                    recent_inception = True
                if not recent_inception:
                    metadata['imageurl'] = image_match.group(1)
                    metadata['imageurlformat'] = 'Q2195' #JPEG
                #    metadata['imageurllicense'] = 'Q18199165' # cc-by-sa.40
                    metadata['imageoperatedby'] = 'Q7005718'
                #    # Can use this to add suggestions everywhere
                #    metadata['imageurlforce'] = True
            yield metadata
        #print('Sleep before next search')
        #time.sleep(30)


def main(*args):
    dictGen = get_mbaq_generator()
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
