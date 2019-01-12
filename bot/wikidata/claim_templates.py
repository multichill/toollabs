#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add the first claim (statement) to items on Wikidata.

The bot works on lists linked from https://www.wikidata.org/wiki/Wikidata:Database_reports/without_claims_by_site like
for example https://www.wikidata.org/wiki/Wikidata:Database_reports/without_claims_by_site/nlwiki . The bot takes it's
configuration from the pages listed at https://www.wikidata.org/wiki/User:NoclaimsBot#Overview like for example
https://nl.wikipedia.org/wiki/Gebruiker:NoclaimsBot/Template_claim . The bot combines this and adds statements where
possible.

You can fire up the bot without any arguments and it will process all configured sources.
If you run it like "claim_templates.py -source:nl", it will only work on that source.

TODO: Could probably move the configuration to some json under https://www.wikidata.org/wiki/User:NoclaimsBot

"""

import pywikibot
from pywikibot import pagegenerators as pg
import re

class TemplateClaimBot:
    """
    A bot to add the first claims based on template used on the linked article
    """
    def __init__(self, lang, noclaims, templateclaims):
        """
        Arguments:
            * lang           - The language code of the Wikipedia we're working on
            * noclaims       - The title of the page on Wikidata with the list of pages to work on
            * templateclaims - The title of the page on Wikipedia with the template claims

        """
        self.lang = lang
        self.site = pywikibot.Site(self.lang, u'wikipedia')
        self.repo = self.site.data_repository()
        self.generator = pg.PreloadingGenerator(pg.NamespaceFilterPageGenerator(self.getNoclaimGenerator(noclaims), 0))
        self.templateclaims = templateclaims
        self.templates = self.getTemplateClaims(templateclaims)

    def getNoclaimGenerator(self, pageTitle):
        """
        Get a generator based on the contents of pageTitle
        """
        page = pywikibot.Page(self.repo, title=pageTitle)

        text = page.get()

        regex = u'^\* \[\[(?P<item>Q\d+)\]\] - \[\[:%s:(?P<article>[^\]]+)\]\]' % (self.lang,)

        for match in re.finditer(regex, text, flags=re.M):
            yield pywikibot.Page(pywikibot.Link(match.group("article"), self.site))

    def getTemplateClaims(self, pageTitle):
        """
        Get a dictionary of templates and the statements to add
        """
        page = pywikibot.Page(self.site, title=pageTitle)
        text = page.get()
        regex = u'^\* \[\[(?P<title>%s:[^\]]+)\]\]\s*(?P<P1>P\d+)\s*(?P<Q1>Q\d+)\s*((?P<P2>P\d+)\s*(?P<Q2>Q\d+))?\s*((?P<P3>P\d+)?\s*(?P<Q3>Q\d+))?$' % (self.site.namespace(10),)
        result = {}

        for match in re.finditer(regex, text, flags=re.M):
            result[match.group('title')] = [(match.group('P1'), match.group('Q1'))]
            if match.group('Q2'):
                result[match.group('title')].append((match.group('P2'), match.group('Q2')))
            if match.group('Q3'):
                result[match.group('title')].append((match.group('P3'), match.group('Q3')))
        return result

    def run(self):
        """
        Just over the pages. Could probably subclass this to bot and use treat()
        """
        for page in self.generator:
            self.processPage(page)

    def processPage(self, page):
        """
        Process a single page
        """
        for pagetemplate in page.itertemplates():
            templatetitle = pagetemplate.title()
            if templatetitle in self.templates.keys():
                pywikibot.output(u'Working on %s using %s' % (page.title(), templatetitle))
                claimslist = self.templates.get(templatetitle)
                try:
                    item = page.data_item()
                    data = item.get()
                    claims = data.get('claims')

                    for pid, qid in claimslist:
                        if pid not in claims:
                            newclaim = pywikibot.Claim(self.repo, pid)
                            claimtarget = pywikibot.ItemPage(self.repo, qid)
                            newclaim.setTarget(claimtarget)
                            summary = u'based on [[%s:%s]] configured on [[%s:%s]]' % (self.lang,
                                                                                       templatetitle,
                                                                                       self.lang,
                                                                                       self.templateclaims)
                            pywikibot.output(summary)
                            item.addClaim(newclaim, summary=summary)
                except pywikibot.exceptions.NoPage:
                    pywikibot.output(u'That page did not exist')
                except pywikibot.exceptions.OtherPageSaveError:
                    pywikibot.output(u'Got some kind of other page save error')
                return


def main(*args):
    """
    The main loop. Possible to add:
    * https://ca.wikipedia.org/wiki/Usuari:NoclaimsBot/Template_claim empty
    * https://de.wikipedia.org/wiki/Benutzer:NoclaimsBot/Template_claim empty
    * https://es.wikipedia.org/wiki/Usuario:NoclaimsBot/Template_claim empty
    * https://sv.wikipedia.org/wiki/Anv%C3%A4ndare:NoclaimsBot/Template_claim
    """
    sources = {u'en' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/enwiki',
                        u'templateclaims' : u'User:NoclaimsBot/Template claim',
                       },
               u'fr' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/frwiki',
                        u'templateclaims' : u'Utilisateur:NoclaimsBot/Template_claim',
                        },
               u'ja' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/jawiki',
                        u'templateclaims' : u'利用者:NoclaimsBot/Template claim',
                        },
               u'nl' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/nlwiki',
                        u'templateclaims' : u'Gebruiker:NoclaimsBot/Template claim',
                       },
               u'sv' : {u'noclaims' : u'Wikidata:Database reports/without claims by site/svwiki',
                        u'templateclaims' : u'Användare:NoclaimsBot/Template claim',
                       },
    }
    source = None

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-source:'):
            if len(arg) == 8:
                source = pywikibot.input(
                        u'Please enter the source property you want to work on:')
            else:
                source = arg[8:]

    if source and source in sources.keys():
        worklangs = [source, ]
    else:
        worklangs = sources.keys()

    for lang in worklangs:
        templateclaimbot = TemplateClaimBot(lang, sources[lang][u'noclaims'], sources[lang][u'templateclaims'])
        templateclaimbot.run()

if __name__ == "__main__":
    main()
