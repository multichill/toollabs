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
                                   'pd-usgov-award',
                                   'pd-usgov-bbg',
                                   'pd-usgov-blm',
                                   'pd-usgov-cfpb',
                                   'pd-usgov-cia',
                                   'pd-usgov-cia-wf',
                                   'pd-usgov-congress',
                                   'pd-usgov-congress-aoc',
                                   'pd-usgov-congress-speaker',
                                   'pd-usgov-dhs',
                                   'pd-usgov-doc',
                                   'pd-usgov-doc-census',
                                   'pd-usgov-doe',
                                   'pd-usgov-doj',
                                   'pd-usgov-dol',
                                   'pd-usgov-dos',
                                   'pd-usgov-dot',
                                   'pd-usgov-dva',
                                   'pd-usgov-ed',
                                   'pd-usgov-epa',
                                   'pd-usgov-fbi',
                                   'pd-usgov-fda',
                                   'pd-usgov-fema',
                                   'pd-usgov-ferc',
                                   'pd-usgov-fsa',
                                   'pd-usgov-fws',
                                   'pd-usgov-gao',
                                   'pd-usgov-gpo',
                                   'pd-usgov-gsa',
                                   'pd-usgov-hhs',
                                   'pd-usgov-hhs-cdc',
                                   'pd-usgov-hhs-nih',
                                   'pd-usgov-hud',
                                   'pd-usgov-interior',
                                   'pd-usgov-interior-usgs-minerals',
                                   'pd-usgov-interior-usgs-nbii',
                                   'pd-usgov-judiciary',
                                   'pd-usgov-military',
                                   'pd-usgov-military-air force',
                                   'pd-usgov-military-air national guard',
                                   'pd-usgov-military-army',
                                   'pd-usgov-military-army-usace',
                                   'pd-usgov-military-army-usacmh',
                                   'pd-usgov-military-army-usaioh',
                                   'pd-usgov-military award',
                                   'pd-usgov-military-badge',
                                   'pd-uscg',  # PD-USGov-Military-Coast Guard
                                   'pd-usgov-military-marines',
                                   'pd-usgov-military-navy',
                                   'pd-usgov-military-national guard',
                                   'pd-usgov-military-nga',
                                   'pd-usgov-military-space force',
                                   'pd-usgov-money',
                                   'pd-usgov-mutcd',
                                   'pd-usgov-nasa',
                                   'pd-usgov-nasa-ap',  # Funky one, remove later
                                   'pd-usgov-nea',
                                   'pd-usgov-nist',
                                   'pd-usgov-noaa',
                                   'pd-usgov-nps',
                                   'pd-usgov-nrc',
                                   'pd-usgov-nrcs',
                                   'pd-usgov-nsa',
                                   'pd-usgov-nsf',
                                   'pd-usgov-ntsb',
                                   'pd-usgov-pc',
                                   'pd-usgov-phs',
                                   'pd-usgov-potus',
                                   'pd-usgov-treasury',
                                   'pd-usgov-tva',
                                   'pd-usgov-usaid',
                                   'pd-usgov-usap',
                                   'pd-usgov-usda',
                                   'pd-usgov-usda-ars',
                                   'pd-usgov-usda-fs',
                                   'pd-usgov-usda-nal',
                                   'pd-usgov-usda-nal-pomological-watercolors',
                                   'pd-usgov-usda-nrcs',
                                   'pd-usgov-usda-nrcs-gallery',
                                   'pd-usgov-usgs',
                                   'pd-usgov-voa',
                                   'pd-usgov-wpa',
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

        media_info = file_page.data_item()
        data = media_info.get('data')
        claims = data.get('statements')

        sdc_action = ''

        if 'P275' in claims:
            # Found a license, something is wrong
            return
        if 'P6216' in claims:
            # Already has a claim, try to update it
            sdc_action = 'change'
            summary = 'updating based on [[%s]]' % (pd_found, )
            if len(claims.get('P6216')) != 1:
                return
            claim = claims.get('P6216')[0]
            if claim.getTarget() != self.pd_item:
                return
            if claim.qualifiers:
                return
        else:
            sdc_action = 'add'
            summary = 'adding based on [[%s]]' % (pd_found, )
            claim = pywikibot.Claim(self.repo, 'P6216')  # copyright status (P6216)
            claim.setTarget(self.pd_item)

        qualifier = pywikibot.Claim(self.repo, 'P1001')  # applies to jurisdiction (P1001)
        qualifier.setTarget(self.usa_item)
        qualifier.isQualifier = True
        claim.qualifiers[qualifier.getID()] = [qualifier]

        qualifier = pywikibot.Claim(self.repo, 'P459')  # determination method (P459)
        qualifier.setTarget(self.work_fed_usa_item)
        qualifier.isQualifier = True
        claim.qualifiers[qualifier.getID()] = [qualifier]

        pywikibot.output(summary)
        if sdc_action == 'change':
            self.site.save_claim(claim, summary=summary, tags='BotSDC')  # T372588 MediaInfo.changeClaim()
        elif sdc_action == 'add':
            media_info.addClaim(claim, summary=summary, tags='BotSDC')  # T372513 to not have the bot crash on the tags

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
