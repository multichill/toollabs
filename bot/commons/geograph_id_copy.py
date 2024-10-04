#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to copy geograph.org.uk image ID (P7384) from qualifier to statement.
"""

import pywikibot
from pywikibot import pagegenerators

class GeographIdCopyBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, generator):
        """
        Grab generator based on search to work on.
        """
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
            self.copy_identifier(filepage)

    def copy_identifier(self, filepage):
        """
        Find and copy the identifier to statement on the filepage

        :param filepage: File to work on
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

        # Check if we already have  geograph.org.uk image ID (P7384)
        if 'P7384' in statements:
            return

        # Check for source of file (P7482)
        if 'P7482' not in statements:
            return

        # Check for file available on the internet (Q74228490)
        file_source_statement = statements.get('P7482')[0]
        if file_source_statement.getTarget().title() != 'Q74228490':
            print(file_source_statement.getTarget().title() )
            return

        # Check if it has the qualifier
        if 'P7384' not in file_source_statement.qualifiers:
            return

        geograph_id = file_source_statement.qualifiers.get('P7384')[0].getTarget()

        summary = f'Copying [[d:Special:EntityPage/P7384]] {geograph_id} from qualifier'
        pywikibot.output(summary)

        new_claim = pywikibot.Claim(self.repo, 'P7384')
        new_claim.setTarget(geograph_id)

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

    geograph_id_copy_bot = GeographIdCopyBot(gen)
    geograph_id_copy_bot.run()


if __name__ == "__main__":
    main()
