#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add Commons category (P373) on items that do have a sitelink to a Commons category

Uses https://commons.wikimedia.org/wiki/Category:Uses_of_Wikidata_Infobox_missing_Commons_Category_statement
"""
import pywikibot
from pywikibot import pagegenerators


class ItemMissingCommonsCategoryBot:
    """
    A bot to Commons Category (P373) links
    """
    def __init__(self):
        """
        No arguments passed
        """
        self.commons = pywikibot.Site('commons', 'commons')
        self.repo = pywikibot.Site().data_repository()
        self.generator = self.get_missing_commons_category_generator()

    def get_missing_commons_category_generator(self):
        """
        Return the items linked from https://commons.wikimedia.org/wiki/Category:Uses_of_Wikidata_Infobox_missing_Commons_Category_statement
        :return: Generator
        """
        category = pywikibot.Category(self.commons, title='Category:Uses of Wikidata Infobox missing Commons Category statement')
        return pagegenerators.SubCategoriesPageGenerator(category)
        #searchstring = 'category: incategory:Uses_of_Wikidata_Infobox_missing_Commons_Category_statement incategory:Uses_of_Wikidata_Infobox'
        #return self.commons.search(searchstring, namespaces=[14])

    def run(self):
        """
        Starts the robot.
        """
            
        for page in self.generator:
            try:
                item_page = pywikibot.ItemPage.fromPage(page)
            except pywikibot.exceptions.NoPageError:
                pywikibot.output('The category %s has no linked item, skipping' % (page.title(),))
                continue

            pywikibot.output('Working on %s / %s' % (page.title(), item_page.title()))
            if not item_page.exists():
                pywikibot.output(u'Item does not exist, skipping')
                continue

            if item_page.isRedirectPage():
                item_page = item_page.getRedirectTarget()
                
            data = item_page.get()
            claims = data.get('claims')

            if 'P373' in claims:
                pywikibot.output('Item already has Commons Category (P373), skipping')
                page.touch()
                continue

            try:
                commons_category_title = item_page.getSitelink(self.commons)
                commons_category = pywikibot.Page(self.commons, title=commons_category_title)
            except pywikibot.exceptions.NoPageError:
                pywikibot.output('Item does not have a sitelink to Commons, skipping')
                continue

            if not commons_category.namespace() == 14:
                pywikibot.output('Linked page is not a category, skipping')

            new_claim = pywikibot.Claim(self.repo, 'P373')
            new_claim.setTarget(commons_category.title(underscore=False, with_ns=False))

            pywikibot.output('Adding %s --> %s' % (new_claim.getID(), new_claim.getTarget()))
            summary = 'Adding missing Commons Category link based on existing sitelink'
            item_page.addClaim(new_claim, summary=summary)
            page.touch()


def main():
    """
    Fire up the bot
    :return:
    """
    item_missing_commons_category_bot = ItemMissingCommonsCategoryBot()
    item_missing_commons_category_bot.run()


if __name__ == "__main__":
    main()
