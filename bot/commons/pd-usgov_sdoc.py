#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add PD-USgov claims to Structured data on Commons
"""

import pywikibot
from pywikibot import pagegenerators
import time


class PDUSGovBot:
    """
    Bot to remove structured data statements on Commons
    """
    def __init__(self, gen, always_touch):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.generator = gen
        self.always_touch = always_touch

        self.pd_usgov_templates = ['pd-usgov',
                                   'pd-usgov-atlas',
                                   'pd-usgov-blm',
                                   'pd-usgov-cia',
                                   'pd-usgov-fws',
                                   'pd-usgov-interior',
                                   'pd-usgov-military',
                                   'pd-usgov-military-air force',
                                   'pd-usgov-military-army',
                                   'pd-usgov-military-navy',
                                   'pd-usgov-nasa',
                                   'pd-usgov-noaa',
                                   'pd-usgov-nps',
                                   'pd-usgov-usgs',
                                   ]

        self.pd_item = pywikibot.ItemPage(self.repo, 'Q19652')
        self.usa_item = pywikibot.ItemPage(self.repo, 'Q30')
        self.work_fed_usa_item = pywikibot.ItemPage(self.repo, 'Q60671452')

    def run(self):
        """
        Run on the items
        """
        for file_page in self.generator:
            try:
                if not file_page.exists():
                    continue
                self.process_file(file_page)
                file_page.touch()
            except pywikibot.exceptions.Error:
                # Just sleep for 1 minute and continue
                pywikibot.output('Got an error while working on %s' % (file_page.title(),) )
                time.sleep(60)

    def process_file(self, file_page):
        """
        """
        pd_found = False
        for template in file_page.templates():
            lower_template = template.title(underscore=False, with_ns=False).lower()
            if lower_template in self.pd_usgov_templates:
                pd_found = template.title()
                break

        if not pd_found:
            return

        summary = 'based on [[%s]]' % (pd_found, )

        media_info = file_page.data_item()
        data = media_info.get('data')
        claims = data.get('statements')

        if 'P275' in claims:
            # Found a license, something is wrong
            return
        if 'P6216' in claims:
            # TODO: Already has copyright status, expand later
            return

        new_claim = pywikibot.Claim(self.repo, 'P6216')  # copyright status (P6216)
        new_claim.setTarget(self.pd_item)

        qualifier = pywikibot.Claim(self.repo, 'P1001')  # applies to jurisdiction (P1001)
        qualifier.setTarget(self.usa_item)
        qualifier.isQualifier = True
        new_claim.qualifiers[qualifier.getID()] = [qualifier]

        qualifier = pywikibot.Claim(self.repo, 'P459')  # determination method (P459)
        qualifier.setTarget(self.work_fed_usa_item)
        qualifier.isQualifier = True
        new_claim.qualifiers[qualifier.getID()] = [qualifier]

        print(summary)
        media_info.addClaim(new_claim, summary=summary, tags='BotSDC')  # T372513 to not have the bot crash on the tags


def main(*args):
    always_touch = False
    gen = None
    gen_factory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-alwaystouch':
            always_touch = True
        elif gen_factory.handle_arg(arg):
            continue

    gen = pagegenerators.PageClassGenerator(gen_factory.getCombinedGenerator(gen, preload=True))

    pd_us_gov_bot = PDUSGovBot(gen, always_touch)
    pd_us_gov_bot.run()


if __name__ == "__main__":
    main()
