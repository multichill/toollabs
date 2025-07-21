#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to find files with coordinates only in exif, tag these files and import the data
"""

import re
import pywikibot
from pywikibot import pagegenerators

class ExifCoordinatesBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, generator, only_tag=False):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site('commons', 'commons')
        self.repo = self.site.data_repository()
        self.generator = generator
        self.only_tag = only_tag

    def run(self):
        """
        Run on the items
        """
        for file_page in self.generator:
            try:
                if file_page.isRedirectPage():
                    file_page = file_page.getRedirectTarget()
                if self.only_tag:
                    self.tag_file_page(file_page)
            except pywikibot.exceptions.NoPageError:
                # Page got deleted, nothing left to do
                pass

    def tag_file_page(self, file_page):
        """
        Tag a single file page for EXIF
        :param file_page:
        :return:
        """
        text = file_page.get()
        if 'GPS EXIF' in text:
            return
        # Filter out
        # Template:Location
        # Category:Location_not_applicable
        # Category:Ambiguous location in EXIF
        # Might give some false positives
        if 'location' in text.lower():
            return
        #print(text)
        new_text = re.sub('(\}\})([\n\r\s]+==\s*\{\{int:license-header\}\}\s*==)', ('\\1{{GPS EXIF}}\\2'), text)
        if text == new_text:
            new_text = '{{GPS EXIF}}\n' + text
            print(new_text)
        pywikibot.showDiff(text, new_text)
        summary = 'Found GPS coordinates in EXIF'
        file_page.put(new_text, summary)

def get_recent_changes_candidates_generator():
    """

    :return:
    """
    site = pywikibot.Site('commons', 'commons')
    parameters = {
        'generator': 'recentchanges',
        'grcnamespace': '6',
        'grctype': 'log',
        'grclimit' : 1000,
        'grcdir': 'newer',
        'prop': 'imageinfo|pageprops|templates|categories',
        'iiprop': 'metadata',
        'tltemplates': 'Template:Location|Template:GPS EXIF',
        'clcategories': 'Category:Location not applicable|Category:Ambiguous location in EXIF',
    }
    gen = pywikibot.data.api.QueryGenerator(site=site, parameters=parameters)
    for gen_result in gen:
        if 'pageprops' in gen_result:
            if 'kartographer_links' in gen_result.get('pageprops'):
                continue
        if 'templates' in gen_result:
            continue
        if 'categories' in gen_result:
            continue
        if 'imageinfo' in gen_result:
            image_info = gen_result.get('imageinfo')[0]
            if image_info:
                metadata = image_info.get('metadata')
                if metadata:
                    for metadata_field in metadata:
                        if metadata_field.get('name') == 'GPSLatitude':
                            print(gen_result['title'])
                            print(image_info)
                            page = pywikibot.FilePage(site, gen_result['title'])
                            yield page

def get_mysql_exif_generator():
    """
    Do a mysql query on the Commons database to get the candidates
    :return:
    """
    site = pywikibot.Site('commons', 'commons')
    query = """SELECT page_namespace, page_title FROM filerevision
JOIN file on fr_id=file_latest
AND fr_file=file_id
JOIN page on page_title=file_name
AND page_namespace=6
LEFT JOIN templatelinks ON page_id=tl_from
AND tl_from_namespace=6
AND (tl_target_id=204 /* Template:Location */
OR tl_target_id=402219 /* Template:GPS_EXIF */
OR tl_target_id=119006506) /* Template:GPS_EXIF_ambiguous */
WHERE fr_metadata LIKE '%GPSLatitude%'
AND tl_from IS NULL
LIMIT 25000"""
    generator=pagegenerators.MySQLPageGenerator(query, site=site)
    for page in generator:
        file_page = pywikibot.FilePage(page)
        yield file_page

def main(*args):
    """

    :param args:
    :return:
    """
    gen = None
    only_tag = False

    gen_factory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-recentchangesexif':
            gen = get_recent_changes_candidates_generator()
        if arg == '-mysqlexif':
            gen = get_mysql_exif_generator()
        elif arg == '-onlytag':
            only_tag = True
        elif gen_factory.handle_arg(arg):
            continue

    gen = pagegenerators.PageClassGenerator(gen_factory.getCombinedGenerator(gen, preload=True))
    exif_coordinates_bot = ExifCoordinatesBot(gen, only_tag=only_tag)
    exif_coordinates_bot.run()


if __name__ == "__main__":
    main()
