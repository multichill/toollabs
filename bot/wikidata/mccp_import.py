#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
The Central Collecting Point München has a paper card based database. Try to get the paintings.

Works on https://www.dhm.de/datenbank/ccp/dhm_ccp.php?seite=6&fld_1=&fld_3=&fld_4=Restitutionskartei&fld_5=&fld_6=&fld_6a=&fld_7=Oil&fld_8=&fld_9=&fld_10=&fld_11=&fld_12_a=&fld_12_b=&fld_12a=&fld_13=&suchen=Suchen

We're searching for oil in the "Restitutionskartei" (return cards). Use beautifulsoup to make sense of this.

"""
import artdatabot
import pywikibot
import urllib3
import requests
import re
import html
from bs4 import BeautifulSoup

def get_mccp_generator():
    """
    Search for paintings and loop over it. Have to use a session to get this data
    :param collectionid: The Wikidata id of the collection to return from
    :return: Generator for artdatabot
    """
    ignore_fields = [ 'Kartei:',
                      'Karteikasten:',
                      'Eigentümer:',
                      ]
    materials = { 'Öl auf Leinwand' : 'oil on canvas',
                  'oil on canvas' : 'oil on canvas',
                  'oil on canv.' : 'oil on canvas',
                  'oil ow canvas' : 'oil on canvas',
                  'oil of canvas' : 'oil on canvas',
                  'oil on metal' : 'oil on metal',
                  'oil on panel' : 'oil on panel',
                  'oil of panel' : 'oil on panel',
                  'oil on penael' : 'oil on panel',
                  'oil on paste' : 'oil on paste',
                  'oil on ivory' : 'oil on ivory',
                  'oil on copper' : 'oil on copper',
                  'oil on paper' : 'oil on paper',
                  'oil on cardboard' : 'oil on cardboard',
                  'oil on oak' : 'oil on oak panel',
                  }
    urllib3.disable_warnings()

    session = requests.Session()
    session.get('https://www.dhm.de/datenbank/ccp/dhm_ccp.php?seite=6&fld_1=&fld_3=&fld_4=Restitutionskartei&fld_5=&fld_6=&fld_6a=&fld_7=Oil&fld_8=&fld_9=&fld_10=&fld_11=&fld_12_a=&fld_12_b=&fld_12a=&fld_13=&suchen=Suchen')
    base_search_url = 'https://www.dhm.de/datenbank/ccp/dhm_ccp.php?seite=8&current=%s'

    for i in range(0, 15500, 20):
        search_url = base_search_url % (i,)
        print (search_url)
        search_page = session.get(search_url) # , verify=False)
        soup = BeautifulSoup(search_page.text, 'html.parser')

        for item_table in soup.find_all('table', 'karteikarte'):
            metadata = {}
            raw_metadata = {}
            for item_entry in item_table.find_all('tr'):
                item_fields = item_entry.find_all('td')
                if len(item_fields)==2:
                    field_name = item_fields[0].text
                    field_value = item_fields[1].text
                    raw_metadata[field_name] = field_value
                    if field_name in ignore_fields:
                        pass
                    elif field_name=='Münchener Nr.:':
                        # https://www.dhm.de/datenbank/ccp/mu.php?no=900/4
                        if not '[' in field_value:
                            metadata['collectionqid']= 'Q1053735'
                            metadata['collectionshort'] = 'MCCP'
                            metadata['locationqid'] = 'Q1053735'
                            metadata['id'] = field_value
                            metadata['idpid'] = 'P217'
                            metadata['artworkidpid'] = 'P10760'
                            metadata['artworkid'] = field_value
                        metadata['url'] = 'https://www.dhm.de/datenbank/ccp/mu.php?no=%s' % (field_value,)
                    elif field_name=='Linz-Nr. (laut Karte):' or field_name=='Linz-Nr. (laut DB Sonderauftrag Linz):':
                        # Add Linz collection and inventory number
                        metadata['extraid'] = field_value
                        metadata['extracollectionqid'] = 'Q475667'
                    elif field_name=='Objekt:':
                        title = html.unescape(field_value).strip()
                        metadata['title'] = { 'en' : title, # Americans so mostly English
                                              }
                    elif field_name=='Datierung:':
                        provenance_regex = '^(\d\d\d\d)\.(\d\d)\.(\d\d)\s*\((Eingang\/Receipt|Ausgang\/Issue)\)$'
                        provenance_match = re.match(provenance_regex, field_value)
                        if provenance_match:
                            provenance_date = '%s-%s-%s' % (provenance_match.group(1),provenance_match.group(2),provenance_match.group(3))
                            if provenance_match.group(4)=='Eingang/Receipt':
                                metadata['acquisitiondate'] = provenance_date
                            elif provenance_match.group(4)=='Ausgang/Issue':
                                metadata['deaccessiondate'] = provenance_date
                        else:
                            print('Unable to parse provenance date %s' % (field_value,))
                    elif field_name=='Datierung (Objekt):':
                        # 1701/1800 / 18. Jhd. and the likes. Not extremely useful, maybe later
                        # print (field_value)
                        pass
                    elif field_name=='Künstler (Transkript):' or field_name=='Künstler:':
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
                    elif field_name=='Material/Technik:':
                        if field_value in materials:
                            metadata['medium'] = materials.get(field_value)
                            # It's a painting
                            metadata['instanceofqid'] = 'Q3305213'
                        elif field_value.lower() in materials:
                            metadata['medium'] = materials.get(field_value.lower())
                            metadata['instanceofqid'] = 'Q3305213'
                    elif field_name=='Höhe:':
                        metadata['heightcm'] = field_value
                    elif field_name=='Breite:':
                        metadata['widthcm'] = field_value
                    elif field_name=='Länge:':
                        # Just put this one in width too
                        metadata['widthcm'] = field_value
                    elif field_name=='Schlagwort:':
                        # All sorts of stuff in here
                        if field_value=='Porträt':
                            metadata['genreqid'] = 'Q134307'
                    elif field_name=='Herkunft/Verbleib/Sozietät:':
                        # This one needs more attention. Plenty of provenance info to find here
                        field_value = field_value.strip()
                        print (field_value)
                        # Cracow, Poland; Warsaw; National Museum
                        if field_value.startswith('Budapest, Hung. Museum of Fine Arts'):
                            metadata['extracollectionqid2'] = 'Q840886' # Museum of Fine Arts, Budapest

                        pass
                    else:
                        print ('Unknown field name "%s" with contents "%s"' % (field_name, field_value))

            if metadata.get('id') and metadata.get('medium') :
                yield metadata
            else:
                print (raw_metadata)
            continue

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


def main(*args):
    dict_gen = get_mccp_generator()
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
