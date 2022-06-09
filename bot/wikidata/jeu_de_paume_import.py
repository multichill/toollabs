#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
The Jeu de Paume was a site where Nazi plunder was documented. Database available online

Works on https://www.errproject.org/jeudepaume/card_advanced_search.php?Query=*&ArtTypeId=246&MaxPageDocs=50

This returns all paintings. Just loop over the individual paintings like
https://www.errproject.org/jeudepaume/card_show.php?Query=%2A&ArtTypeId=246&StartDoc=1

Use beautifulsoup to make sense of this.
"""
import artdatabot
import pywikibot
import urllib3
import requests
import re
import html
from bs4 import BeautifulSoup

def get_jeu_de_paume_generator():
    """
    Just loop over all the individual records
    Search for paintings and loop over it. Have to use a session to get this data
    :return: Generator for artdatabot
    """
    ignore_fields = []
    urllib3.disable_warnings()

    session = requests.Session()
    session.get('https://www.errproject.org/jeudepaume/card_advanced_search.php?Query=*&ArtTypeId=246&MaxPageDocs=50', verify=False)
    base_search_url = 'https://www.errproject.org/jeudepaume/card_show.php?Query=%%2A&ArtTypeId=246&StartDoc=%s'

    for i in range(1, 11729):
        metadata = {}
        search_url = base_search_url % (i,)
        print (search_url)
        search_page = session.get(search_url, verify=False)
        print (search_page.url)
        jeu_de_paume_id = search_page.url.replace('https://www.errproject.org/jeudepaume/card_view.php?CardId=', '')
        metadata['artworkidpid'] = 'P10750'
        metadata['artworkid'] = jeu_de_paume_id
        metadata['url'] = search_page.url

        soup = BeautifulSoup(search_page.text, 'html.parser')
        item_table = soup.find('div', id='content').find('table')

        raw_metadata = {}
        for item_entry in item_table.find_all('tr'):
            if item_entry.find('th'):
                #print (item_entry)
                field_name = item_entry.find('th').text
                field_value_raw = item_entry.find('td')
                field_value = field_value_raw.text
                # This will overwrite some fields
                if not field_name=='Images:':
                    raw_metadata[field_name] = field_value

                if field_name in ignore_fields:
                    pass
                elif field_name=='Munich No.:':
                    # https://www.dhm.de/datenbank/ccp/mu.php?no=900/4
                    if not '[' in field_value:
                        metadata['collectionqid']= 'Q1053735'
                        metadata['collectionshort'] = 'MCCP'
                        metadata['locationqid'] = 'Q1053735'
                        metadata['id'] = field_value
                        metadata['idpid'] = 'P217'

                #elif field_name=='Linz-Nr. (laut Karte):' or field_name=='Linz-Nr. (laut DB Sonderauftrag Linz):':
                #    # Add Linz collection and inventory number
                #    metadata['extraid'] = field_value
                #    metadata['extracollectionqid'] = 'Q475667'
                elif field_name=='Medium:':
                    if field_value=='Paintings':
                        metadata['instanceofqid'] = 'Q3305213'
                elif field_name=='Title:':
                    title = html.unescape(field_value).strip()
                    metadata['title'] = { 'de' : title, # Germans
                                          }
                #elif field_name=='Datierung:':
                #    provenance_regex = '^(\d\d\d\d)\.(\d\d)\.(\d\d)\s*\((Eingang\/Receipt|Ausgang\/Issue)\)$'
                #    provenance_match = re.match(provenance_regex, field_value)
                #    if provenance_match:
                #        provenance_date = '%s-%s-%s' % (provenance_match.group(1),provenance_match.group(2),provenance_match.group(3))
                #        if provenance_match.group(4)=='Eingang/Receipt':
                #            metadata['acquisitiondate'] = provenance_date
                #        elif provenance_match.group(4)=='Ausgang/Issue':
                #            metadata['deaccessiondate'] = provenance_date
                #    else:
                #        print('Unable to parse provenance date %s' % (field_value,))
                #elif field_name=='Datierung (Objekt):':
                #    # 1701/1800 / 18. Jhd. and the likes. Not extremely useful, maybe later
                #    # print (field_value)
                #    pass
                elif field_name=='Artist:':
                    name = html.unescape(field_value).strip()
                    name_regex = '^([^,]+), ([^\(]+)$'
                    name_match = re.match(name_regex, name)

                    if name_match:
                        name = '%s %s' % (name_match.group(2), name_match.group(1))
                    metadata['creatorname'] = name
                    metadata['description'] = { 'de' : '%s von %s' % ('Gemälde', metadata.get('creatorname'),),
                                                'nl' : '%s van %s' % ('schilderij', metadata.get('creatorname'),),
                                                'en' : '%s by %s' % ('painting', metadata.get('creatorname'),),
                                                }
                #elif field_name=='Material/Technik:':
                #    if field_value in materials:
                #        metadata['medium'] = materials.get(field_value)
                #        # It's a painting
                #        metadata['instanceofqid'] = 'Q3305213'
                #    elif field_value.lower() in materials:
                #        metadata['medium'] = materials.get(field_value.lower())
                #        metadata['instanceofqid'] = 'Q3305213'
                #elif field_name=='Höhe:':
                #    metadata['heightcm'] = field_value
                #elif field_name=='Breite:':
                #    metadata['widthcm'] = field_value
                #elif field_name=='Länge:':
                #    # Just put this one in width too
                #    metadata['widthcm'] = field_value
                #elif field_name=='Schlagwort:':
                #    # All sorts of stuff in here
                #    if field_value=='Porträt':
                #        metadata['genreqid'] = 'Q134307'
                #elif field_name=='Herkunft/Verbleib/Sozietät:':
                #    # This one needs more attention. Plenty of provenance info to find here
                #    field_value = field_value.strip()
                #    print (field_value)
                #    # Cracow, Poland; Warsaw; National Museum
                #    if field_value.startswith('Budapest, Hung. Museum of Fine Arts'):
                #        metadata['extracollectionqid2'] = 'Q840886' # Museum of Fine Arts, Budapest
                #    pass
                #else:
                #    print ('Unknown field name "%s" with contents "%s"' % (field_name, field_value))

        if metadata.get('id') and metadata.get('instanceofqid') :
            yield metadata
        #else:
        #    print (raw_metadata)
        continue
        """
            if date_field_match:
                date_field = date_field_match.group(1)
                dateregex = u'^(\d\d\d\d)$'
                datecircaregex = u'^(\d\d\d\d)\s*\(um\)\s*$'
                periodregex = u'^(\d\d\d\d)[-\/](\d\d\d\d)$'
                circaperiodregex = u'(\d\d\d\d)[-\/](\d\d\d\d)\s*\(um\)\s*$' # No hits I think

                datematch = re.match(dateregex, date_field)
                datecircamatch = re.match(datecircaregex, date_field)
                periodmatch = re.match(periodregex, date_field)
                circaperiodmatch = re.match(circaperiodregex, date_field)

                if datematch:
                    # Don't worry about cleaning up here.
                    metadata['inception'] = int(datematch.group(1))
                elif datecircamatch:
                    metadata['inception'] = int(datecircamatch.group(1))
                    metadata['inceptioncirca'] = True
                elif periodmatch:
                    metadata['inceptionstart'] = int(periodmatch.group(1),)
                    metadata['inceptionend'] = int(periodmatch.group(2),)
                elif circaperiodmatch:
                    metadata['inceptionstart'] = int(circaperiodmatch.group(1),)
                    metadata['inceptionend'] = int(circaperiodmatch.group(2),)
                    metadata['inceptioncirca'] = True
                else:
                    print (u'Could not parse date: "%s"' % (date_field,))

            # Not that good quality images, but it makes matching a lot easier
            image_regex = '\<img src\=\"(img\.php\?laufnr\=LI\d+)\" alt\=\"LI[^\"]+\" class\=\"card-img\" border\=\"0\"\>'
            image_match = re.search(image_regex, item_page_data)

            if image_match:
                image_url = 'https://www.dhm.de/datenbank/linzdbv2/%s' % (image_match.group(1),)
                # To filter out the placeholders
                imageresponse = requests.get(image_url, stream=True, verify=False)
                if len(imageresponse.text) > 5000:
                    metadata[u'imageurl'] = image_url
                    metadata[u'imageurlformat'] = u'Q2195' #JPEG
                    metadata[u'imageoperatedby'] = 'Q688335'
                    # Could use this later to force
                    # metadata[u'imageurlforce'] = True
        """

def main(*args):
    dict_gen = get_jeu_de_paume_generator()
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
