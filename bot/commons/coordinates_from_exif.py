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
        #self.site.login()
        #self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.generator = generator
        self.only_tag = only_tag

    def run(self):
        """
        Run on the items
        """
        for file_page in self.generator:
            if file_page.isRedirectPage():
                file_page = file_page.getRedirectTarget()
            if self.only_tag:
                self.tag_file_page(file_page)

            #self.extract_identifiers(filepage)

    def tag_file_page(self, file_page):
        """
        Tag a single file page for EXIF
        :param file_page:
        :return:
        """
        text = file_page.get()
        if 'GPS EXIF' in text:
            return
        #print(text)
        new_text = re.sub('(\}\})([\n\r\s]+==\s*\{\{int:license-header\}\}\s*==)', ('\\1{{GPS EXIF}}\\2'), text)
        if text == new_text:
            new_text = '{{GPS EXIF}}\n' + text
            print(new_text)
        pywikibot.showDiff(text, new_text)
        summary = 'Found GPS coordinates in EXIF'
        file_page.put(new_text, summary)

    def extract_identifiers(self, filepage):
        """

        :param filepage:
        :return:
        """
        mediainfo = filepage.data_item()
        if not mediainfo:
            return

        try:
            statements = mediainfo.statements
        except Exception:
            # Bug in Pywikibot, no statements
            return
        for id_template, id_info in self.id_templates.items():
            self.extract_identifier(filepage, mediainfo, id_template, id_info.get('property'), id_info.get('regex'))

    def extract_identifier(self, filepage, mediainfo, id_template, id_property, regex):
        """
        Find and copy the identifier from the wikitext to a statement on the filepage

        :param filepage: File to work on
        :param id_template: Template to look for
        :param id_property: The property to add
        :param regex: Regex to use to extract the data
        :return:
        """

        # Check if we already have the property
        if id_property in mediainfo.statements:
            pywikibot.output(f'{id_property} found')
            return

        template_found = False
        for template in filepage.itertemplates():
            if template.title() == id_template:
                template_found = True
                break

        if not template_found:
            pywikibot.output(f'{id_template} not found')
            return False

        match = re.search(regex, filepage.text)
        if not match:
            pywikibot.output(f'{regex} did not match')
            return

        found_id = match.group('id')

        summary = f'Extracted [[d:Special:EntityPage/{id_property}]] {found_id} from [[{id_template}]]'
        pywikibot.output(summary)

        new_claim = pywikibot.Claim(self.repo, id_property)
        new_claim.setTarget(found_id)

        data = {'claims': [new_claim.toJSON(), ]}
        try:
            # FIXME: Switch to mediainfo.editEntity() https://phabricator.wikimedia.org/T376955
            response = self.site.editEntity(mediainfo, data, summary=summary, tags='BotSDC')
            filepage.touch()
        except pywikibot.exceptions.APIError as e:
            print(e)

def get_recent_changes_canditates_generator():
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
        #print(gen_result)
        if 'pageprops' in gen_result:
            if 'kartographer_links' in gen_result.get('pageprops'):
                #print('Already has kartographer_links')
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
            gen = get_recent_changes_canditates_generator()
        elif arg == '-onlytag':
            only_tag = True
        elif gen_factory.handle_arg(arg):
            continue


    gen = pagegenerators.PageClassGenerator(gen_factory.getCombinedGenerator(gen, preload=True))
    #for bla in gen:
    #    print(bla)
    #    pass
    exif_coordinates_bot = ExifCoordinatesBot(gen, only_tag=only_tag)
    exif_coordinates_bot.run()


if __name__ == "__main__":
    main()
