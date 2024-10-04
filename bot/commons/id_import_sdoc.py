#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import id's from wikitext into Structured data on Commons

"""

import re
import pywikibot
from pywikibot import pagegenerators

class IdImportBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, generator):
        """
        Grab generator based on search to work on.
        """
        self.id_templates = {'Template:ID-USMil': {
            'regex': '\{\{ID-USMil\s*\|\s*(1\=)?\s*(?P<id>([0-9]{2})(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])-(F|A|G|D|H|S|P|M|Z|N|O|X)-(\d{4}[A-Z]|[A-Z]{2}\d{3})-\d{3,4})\s*(\||\})',
            'property': 'P12967'},
                             }

        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.generator = generator

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            print(filepage.title())
            self.extract_identifiers(filepage)

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
            response = self.site.editEntity(mediainfo, data, summary=summary)
            filepage.touch()
        except pywikibot.exceptions.APIError as e:
            print(e)


def main(*args):
    """

    :param args:
    :return:
    """
    #site = pywikibot.Site('commons', 'commons')
    gen = None

    gen_factory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-loose':
            pass
        elif gen_factory.handle_arg(arg):
            continue

    gen = pagegenerators.PageClassGenerator(gen_factory.getCombinedGenerator(gen, preload=True))

    id_import_bot = IdImportBot(gen)
    id_import_bot.run()


if __name__ == "__main__":
    main()
