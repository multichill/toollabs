#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to work on images with taken on to add inception to SDoC (structured data on Commons).

Will generally work on https://commons.wikimedia.org/wiki/Category:Taken_on_missing_SDC_inception
Other generators are possible too

Special care for instances of multiple works

"""

import pywikibot
import re
import pywikibot.data.sparql
from pywikibot import pagegenerators

class TakenOnBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, gen, loose, always_touch):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site(u'commons', u'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()

        self.generator = gen
        self.loose = loose
        self.always_touch = always_touch

        self.wikimedia_commons_file = pywikibot.ItemPage(self.repo, 'Q51954352')

    def run(self):
        """
        Run on the items
        """
        for file_page in self.generator:
            pywikibot.output(file_page.title())
            if not file_page.exists():
                continue
            date = self.extract_taken_on_date(file_page)
            if not date:
                continue
            applies_to_commons_file = self.get_multiple_works(file_page)
            self.update_inception(file_page, date, applies_to_commons_file)

    def extract_taken_on_date(self, file_page):
        """
        Extract the taken on date based on category.
        :param file_page:
        :return: String with date or False if not found
        """
        date_regex = '^.*photographs taken on (?P<date>\d\d\d\d-\d\d-\d\d)$'
        date_string = False
        for category in file_page.categories():
            category_name = category.title(underscore=False, with_ns=False)
            date_match = re.match(date_regex, category_name, flags=re.IGNORECASE)
            if date_match:
                date_string = date_match.group('date').strip()
                break

        return date_string

    def get_multiple_works(self, file_page):
        """
        Check if the file page is containing multiple works
        :param file_page: The file page to work on
        :return: True or False
        """
        multiple_works_templates = ['artwork', 'art photo']
        for template in file_page.templates():
            template_name = template.title(underscore=False, with_ns=False).lower()
            if template_name in multiple_works_templates:
                return True
        multiple_work_claims = ['P921',  # main subject
                                'P6243',  # digital representation of
                                ]
        mediainfo = file_page.data_item()
        for claim_id in mediainfo.statements.keys():
            if claim_id in multiple_work_claims:
                return True
        return False

    def update_inception(self, file_page, date, applies_to_commons_file):
        """
        Add or update the SDC inception for the file
        :param file_page: The file page to work on
        :param date: String containing the date
        :param applies_to_commons_file: Boolean if the date applies to Commons file
        :return: Nothing, edit in place
        """
        mediainfo = file_page.data_item()
        if 'P571' in mediainfo.statements:
            if applies_to_commons_file:
                print('Already has inception, might need qualifier. Implement later')
            else:
                pywikibot.output('Inception is already on the file. All done.')

            if self.always_touch:
                file_page.touch()
            return

        year_month_day_regex = '^(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)$'
        year_month_day_match = re.match(year_month_day_regex, date)
        if not year_month_day_match:
            pywikibot.output(f'Unable to extract date from {date}')
            return
        year = int(year_month_day_match.group('year'))
        month = int(year_month_day_match.group('month'))
        day = int(year_month_day_match.group('day'))

        date_value = pywikibot.WbTime(year=year, month=month, day=day)

        new_claim = pywikibot.Claim(self.repo, 'P571')
        new_claim.setTarget(date_value)

        if applies_to_commons_file and year >= 2000:
            new_qualifier = pywikibot.Claim(self.repo, 'P518') #Applies to part
            new_qualifier.isQualifier = True
            new_qualifier.setTarget(self.wikimedia_commons_file)
            new_claim.qualifiers['P518'] = [new_qualifier]
            summary = f'Adding [[d:Special:EntityPage/P571]] {date} with Commons File qualifier based on taken on category'
        elif applies_to_commons_file:
            summary = f'Adding [[d:Special:EntityPage/P571]] {date} without qualifier (year before 2000) based on taken on category'
        else:
            summary = f'Adding [[d:Special:EntityPage/P571]] {date} based on taken on category'

        pywikibot.output(summary)
        data = {'claims': [new_claim.toJSON(), ]}
        try:
            # FIXME: Switch to mediainfo.editEntity() https://phabricator.wikimedia.org/T376955
            response = self.site.editEntity(mediainfo, data, summary=summary, tags='BotSDC')
            file_page.touch()
        except pywikibot.exceptions.APIError as e:
            print(e)


def main(*args):
    gen = None
    gen_factory = pagegenerators.GeneratorFactory()
    loose = False
    always_touch = False

    for arg in pywikibot.handle_args(args):
        if arg == '-loose':
            loose = True
        elif arg == '-alwaystouch':
            always_touch = True
        elif gen_factory.handle_arg(arg):
            continue
    gen = pagegenerators.PageClassGenerator(gen_factory.getCombinedGenerator(gen, preload=True))

    taken_on_bot = TakenOnBot(gen, loose, always_touch)
    taken_on_bot.run()

if __name__ == "__main__":
    main()
