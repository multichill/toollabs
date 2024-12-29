#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import paintings from the Kunsthaus Zürich to Wikidata.

They seems to use Emuseum with json output

This bot uses artdatabot to upload it to Wikidata.
"""
import artdatabot
import pywikibot
import requests
import re

def get_kunsthaus_generator():
    """
    Generator to return Kunsthaus paintings
    """
    base_search_url = 'https://collection.kunsthaus.ch/solr/published/select?fq=type:Object&fq={!tag=et_category_en_s}category_en_s:(%%22painting%%22)&q=*:*&rows=%s&sort=last_modified_sml%%20desc&start=%s'

    start_url = base_search_url % (1, 0, )

    session = requests.Session()
    start_page = session.get(start_url)
    number_found = start_page.json().get('response').get('numFound')
    print(number_found)

    step = 10

    for i in range(0, number_found + step, step):
        search_url = base_search_url % (step, i,)

        print(search_url)
        search_page = session.get(search_url)

        work_url_regex = '<a href="/Details/collect/(\d+)">'
        matches = re.finditer(work_url_regex, search_page.text)

        for object_docs in search_page.json().get('response').get('docs'):
            metadata = {}
            object_id = object_docs.get('oid')

            url = 'https://collection.kunsthaus.ch/en/collection/item/%s/' % (object_id, )
            json_url = 'https://collection.kunsthaus.ch/_next/data/A2oJ2OIL-osUXZ2b32zHc/en/collection/item/%s.json' % (object_id, )

            pywikibot.output(url)
            pywikibot.output(json_url)

            json_page = session.get(json_url)
            item_json = json_page.json().get('pageProps').get('data').get('item')
            metadata['url'] = url

            ## Add the identifier property when we have created that
            #metadata['artworkidpid'] = 'Pxxx'  # To create
            #metadata['artworkid'] = object_id

            # Only paintings
            metadata['instanceofqid'] = 'Q3305213'
            metadata['idpid'] = 'P217'
            metadata['id'] = item_json.get('Inv. Nr.')

            metadata['collectionqid'] = 'Q685038'
            metadata['collectionshort'] = 'Kunsthaus'
            metadata['locationqid'] = 'Q685038'

            title = item_json.get('ObjTitleTxt').strip()

            # Chop chop, might have long titles
            if len(title) > 220:
                title = title[0:200]
            title = title.replace('\t', '').replace('\n', '')
            metadata['title'] = {'de': title, }

            creator_name = item_json.get('ObjPersonMasonryTxt')
            creator_name_de = item_json.get('ObjPersonMasonryTxt_de')

            if creator_name and creator_name_de:
                metadata['description'] = { 'nl': '%s van %s' % ('schilderij', creator_name,),
                                            'en': '%s by %s' % ('painting', creator_name,),
                                            'de': '%s von %s' % ('Gemälde', creator_name_de, ),
                                            'fr': '%s de %s' % ('peinture', creator_name, ),
                                            }
                metadata['creatorname'] = creator_name

            date = item_json.get('ObjDateTxt')

            if date:
                year_regex = '^\s*(\d\d\d\d)\s*$'
                date_circa_regex = '^ca?\.\s*(\d\d\d\d)$'
                period_regex = '^(\d\d\d\d)\s*[\-\–\/]\s*(\d\d\d\d)$'
                circa_period_regex = '^ca?\.\s*(\d\d\d\d)\s*[\-\–\/]\s*(\d\d\d\d)$'
                short_period_regex = '^(\d\d)(\d\d)[\-\–\/](\d\d)$'
                circa_short_period_regex = '^ca?\.\s*(\d\d)(\d\d)[\-\–\/](\d\d)$'

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

            # acquisition year
            acquisition_year = item_json.get('ObjAcquisitionYearTxt')
            if acquisition_year:
                metadata['acquisitiondate'] = acquisition_year

            materials = item_json.get('ObjMaterialTechniqueTxt')
            if materials:
                metadata['medium'] = materials.lower()

            # The provide free images. Just have to filter out the ones that are copyrighted
            default_image = item_json.get('DefaultImage')

            if default_image:
                for multimedia_item in item_json.get('ObjMultimediaMainImageRef').get('Items'):
                    if not multimedia_item.get('MulPhotocreditTxt'):
                        multimedia_image = multimedia_item.get('Multimedia')[0]
                        if multimedia_image.get('def') == "true":
                            if multimedia_image.get('mime') == 'image/jpeg':
                                metadata['imageurl'] = 'https://collection.kunsthaus.ch/%s' % (multimedia_image.get('extra'))
                                metadata['imageurlformat'] = 'Q27996264'  # JPEG
                                metadata['imageoperatedby'] = 'Q685038'
                                # Can use this to add suggestions everywhere
                                metadata['imageurlforce'] = True

            credit_line = item_json.get('ObjCreditlineTxt')

            if credit_line and credit_line == 'Emil Bührle Collection, on long term loan at Kunsthaus Zürich':
                metadata['extracollectionqid'] = 'Q666331'

            yield metadata


def main(*args):
    dict_gen = get_kunsthaus_generator()
    dry_run = False
    create = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dry_run = True
        elif arg.startswith('-create'):
            create = True

    if dry_run:
        for painting in dict_gen:
            print (painting)
    else:
        art_data_bot = artdatabot.ArtDataBot(dict_gen, create=create)
        art_data_bot.run()


if __name__ == "__main__":
    main()
