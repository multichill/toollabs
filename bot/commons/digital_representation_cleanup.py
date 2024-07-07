#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to clean up files which have digital representation of (P6243).

* These files should also have the same depicts (P180) and  main subject (P921).
* For 3D works, the digital representation of (P6243) should be removed
* For 2D works, the missing digital representation of (P6243) should be added

Should be switched to a more general Pywikibot implementation.

"""

import pywikibot
import re
import pywikibot.data.sparql
import time
import json
from pywikibot import pagegenerators

class DigitalRepresentationCleaanupBot:
    """
    Bot to add structured data statements on Commons
    """
    def __init__(self, gen, alwaystouch, remove3d):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.generator = gen
        self.alwaystouch = alwaystouch
        self.remove3d = remove3d
        (self.works_2d, self.works_3d, self.works_both) = self.load_work_types()

    def load_work_types(self):
        """
        Load the different kinds of works. For now just static lists. Can do it later on the wiki
        :return: The three lists as a tuple
        """
        works_2d = ['Q18396864',  # aquatint print
                    'Q184784',  # architectural drawing
                    'Q89503149',  # chromolithograph
                    'Q93184',  # drawing
                    'Q11835431',  # engraving
                    'Q18218093',  # etching print
                    'Q21281546',  # gouache painting
                    'Q5647631',  # handscroll
                    'Q132137',  # icon
                    'Q15123870',  # lithograph
                    'Q21647744',  # mezzotint print
                    'Q3305213',  # painting
                    'Q12043905'  # pastel
                    'Q125191',  # photograph
                    'Q282129',  # portrait miniature
                    'Q11060274',  # print
                    'Q76504821',  # scenography sketch
                    'Q22669539',  # stipple engraving
                    'Q18761202',  # watercolor painting
                    'Q18219090',  # woodcut print
                    ]
        works_3d = ['Q220659',  # archaeological artifact
                    'Q17489160',  # bust
                    'Q15328',  # camera
                    'Q45621',  # ceramic
                    'Q13464614',  # ceramics
                    'Q15026',  # chair
                    'Q16970',  # church building
                    'Q210272',  # cultural heritage
                    'Q168658',  # doll
                    'Q1066288',  # figurine
                    'Q14745',  # furniture
                    'Q131647',  # medal
                    'Q196538',  # microscope
                    'Q4989906',  # monument
                    'Q16560',  # palace
                    'Q245117',  # relief sculpture
                    'Q722604',  # reliquary
                    'Q48634',  # sarcophagus
                    'Q860861',  # sculpture
                    'Q17489156',  # sculpture capital
                    'Q19479037',  # sculpture serie
                    'Q1457747',  # ship model
                    'Q179700',  # statue
                    'Q11422',  # toy
                    ]
        works_both = ['Q15711026',  # altarpiece
                      'Q475476',  # diptych
                      'Q1278452',  # polyptych
                      'Q46686',  # reredos
                      'Q79218',  # triptych
                      'Q11801536',  # winged altarpiece
                      ]

        return works_2d, works_3d, works_both

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.getCurrentMediaInfo(mediaid)

            pywikibot.output(u'Working on %s' % (filepage.title(),))

            if not filepage.exists():
                continue

            if not filepage.has_permission():
                # Picture might be protected
                continue

            self.resolve_redirects(filepage, mediaid, currentdata)
            self.update_recursive_depicts(filepage, mediaid, currentdata)
            self.addMissingStatementsToFile(filepage, mediaid, currentdata)
            if self.remove3d:
                self.removeDigitalRepresentation3d(filepage, mediaid, currentdata)

    def getCurrentMediaInfo(self, mediaid):
        """
        Check if the media info exists. If that's the case, return that so we can expand it.
        Otherwise return an empty structure with just <s>claims</>statements in it to start
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: json
            """
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M52611909
        # https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&ids=M10038
        request = self.site.simple_request(action='wbgetentities',ids=mediaid)
        data = request.submit()
        if data.get(u'entities').get(mediaid).get(u'pageid'):
            return data.get(u'entities').get(mediaid)
        return {}

    def resolve_redirects(self, filepage, mediaid, currentdata):
        """
        Resolve redirects for
        :param filepage:
        :param mediaid:
        :param currentdata:
        :return:
        """
        if not currentdata.get('statements'):
            return
        for prop in ['P180', 'P921', 'P6243']:
            if currentdata.get('statements').get(prop):
                for statement in currentdata.get('statements').get(prop):
                    if statement.get('mainsnak').get('datavalue'):
                        qid = statement.get('mainsnak').get('datavalue').get('value').get('id')
                        claim_id = statement.get('id')
                        item = pywikibot.ItemPage(self.repo, qid)
                        if item.isRedirectPage():
                            target_item = item.getRedirectTarget()
                            summary = 'resolving redirect'
                            self.update_statement(filepage, claim_id, target_item.title(), summary)

    def update_recursive_depicts(self, filepage, mediaid, currentdata):
        """
        The depicts on the file page should point to the work, not what is visible in the work. Update it
        :param filepage: The page of the file to work on.
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :param currentdata: The current structured data
        :return:
        """
        if not currentdata.get('statements'):
            return
        if not currentdata.get('statements').get('P180'):
            return
        if not len(currentdata.get('statements').get('P180'))==1:
            return
        if not currentdata.get('statements').get('P180')[0].get('mainsnak').get('datavalue'):
            return
        if not currentdata.get('statements').get('P6243'):
            return

        artwork_qid = currentdata.get('statements').get('P6243')[0].get('mainsnak').get('datavalue').get('value').get('id')
        depicts_qid = currentdata.get('statements').get('P180')[0].get('mainsnak').get('datavalue').get('value').get('id')
        depicts_claim_id = currentdata.get('statements').get('P180')[0].get('id')

        if artwork_qid == depicts_qid:
            return

        artwork_item = pywikibot.ItemPage(self.repo, artwork_qid)
        depicts_item = pywikibot.ItemPage(self.repo, depicts_qid)

        if artwork_item.isRedirectPage() or depicts_item.isRedirectPage():
            # Handled in redirect function
            return

        artwork_claims = artwork_item.get().get('claims')

        if 'P180' in artwork_claims:
            for depicts_claim in artwork_claims.get('P180'):
                if depicts_claim.getTarget() == depicts_item:
                    # Found it, update Commons
                    summary = '[[d:Special:EntityPage/P180]]->[[d:Special:EntityPage/%s]] is on [[d:Special:EntityPage/%s]]' % (depicts_qid, artwork_qid)
                    self.update_statement(filepage, depicts_claim_id, artwork_qid, summary)
                    return
            # TODO: We did not find it. Add it to the Wikidata item??
            return
        else:
            # TODO: No depicts on the item. Add it to the Wikidata item??
            return

    def update_statement(self, filepage, claim_id, new_qid, summary='Updating statement'):
        """
        Update the statement on a file on Commons

        :param depicts_claim_id: The id of the statement to update
        :param new_qid: The ID of the Wikidata item to update it to
        :return:
        """
        new_claim =  { 'entity-type' : 'item',
                       'numeric-id': new_qid.replace('Q', ''),
                       'id' : new_qid,
                       }

        token = self.site.tokens['csrf']
        postdata = {'action' : 'wbsetclaimvalue',
                    'format' : 'json',
                    'claim' : claim_id,
                    'snaktype' : 'value',
                    'value' : json.dumps(new_claim),
                    'token' : token,
                    'summary' : summary,
                    'bot' : True,
                    }
        #if currentdata:
        #    # This only works when the entity has been created
        #    postdata['baserevid'] = currentdata.get('lastrevid')

        request = self.site.simple_request(**postdata)
        try:
            data = request.submit()
            # Always touch the page to flush it
            filepage.touch()
        except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
            pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
            # Print the offending token
            print (token)
            time.sleep(30)
            # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
            self. site.tokens.load_tokens(['csrf'])
            # This should be a new token
            print (self.site.tokens['csrf'])


    def addMissingStatementsToFile(self, filepage, mediaid, currentdata):
        """
        Add missing depicts (P180) and main subject (P921) if these are missing

        :param filepage: The page of the file to work on.
        :param mediaid: The entity ID (like M1234, pageid prefixed with M)
        :return: Nothing, edit in place
        """

        # Retrieve the target
        if currentdata.get('statements') and currentdata.get('statements').get('P6243'):
            artworkqid = currentdata.get('statements').get('P6243')[0].get('mainsnak').get('datavalue').get('value').get('id')
        else:
            return

        # Here we're collecting
        newclaims = {}

        # Add depicts (P180) if it's missing
        if not currentdata.get('statements').get('P180'):
            newclaims['depicts'] = self.addClaimJson(mediaid, 'P180', artworkqid)

        # Add main subject (P921) if it's missing
        if not currentdata.get('statements').get('P921'):
            newclaims['main subject'] = self.addClaimJson(mediaid, 'P921', artworkqid)

        addedclaims = []

        itemdata = {u'claims' : [] }

        for newclaim in newclaims:
            if newclaims.get(newclaim):
                itemdata['claims'].extend(newclaims.get(newclaim))
                addedclaims.append(newclaim)

        if len(addedclaims) > 0:
            summary = u'Adding structured data: %s' % (addedclaims[0],)
            if len(addedclaims) > 2:
                for i in range(1, len(addedclaims)-1):
                    summary = summary + u', %s' % (addedclaims[i],)
            if len(addedclaims) > 1:
                summary = summary + u' & %s' % (addedclaims[-1],)

            # Flush it
            pywikibot.output(summary)

            token = self.site.tokens['csrf']
            postdata = {'action' : u'wbeditentity',
                        'format' : u'json',
                        'id' : mediaid,
                        'data' : json.dumps(itemdata),
                        'token' : token,
                        'summary' : summary,
                        'bot' : True,
                        }
            if currentdata:
                # This only works when the entity has been created
                postdata['baserevid'] = currentdata.get('lastrevid')

            request = self.site.simple_request(**postdata)
            try:
                data = request.submit()
                # Always touch the page to flush it
                filepage.touch()
            except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
                pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
                # Print the offending token
                print (token)
                time.sleep(30)
                # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
                self. site.tokens.load_tokens(['csrf'])
                # This should be a new token
                print (self.site.tokens['csrf'])
        elif self.alwaystouch:
            try:
                filepage.touch()
            except:
                pywikibot.output('Got an API error while touching page. Sleeping, getting a new token and skipping')
                self. site.tokens.load_tokens(['csrf'])

    def removeDigitalRepresentation3d(self, filepage, mediaid, currentdata):
        """
        Remove the digital representation statement from 3d works

        We assume the P180 & P921 have been added
        """
        # Retrieve the target
        if currentdata.get('statements') and currentdata.get('statements').get('P6243'):
            artworkqid = currentdata.get('statements').get('P6243')[0].get('mainsnak').get('datavalue').get('value').get('id')
            claimid = currentdata.get('statements').get('P6243')[0].get('id')
        else:
            return

        artworkitem = pywikibot.ItemPage(self.repo, artworkqid)

        if artworkitem.isRedirectPage():
            artworkitem = artworkitem. getRedirectTarget()

        claims = artworkitem.get().get('claims')

        if 'P31' in claims:
            found_2d = 0
            found_3d = 0
            found_both = 0
            found_unknown = 0
            found_3d_example = None
            for claim in claims.get('P31'):
                instanceof = claim.getTarget().title()
                if instanceof in self.works_2d:
                    found_2d += 1
                elif instanceof in self.works_3d:
                    found_3d += 1
                    found_3d_example = instanceof
                elif instanceof in self.works_both:
                    found_both += 1
                else:
                    found_unknown += 1

            if found_3d and not found_2d and not found_both:
                summary = 'removing because [[d:Special:EntityPage/%s]] is an instance of [[d:Special:EntityPage/%s]]' % (artworkqid, found_3d_example)
                pywikibot.output('Removing structured data: %s is an instance of %s' % (artworkqid, found_3d_example))

                token = self.site.tokens['csrf']
                postdata = {'action' : 'wbremoveclaims',
                            'format' : 'json',
                            'claim' : claimid,
                            'token' : token,
                            'summary' : summary,
                            'bot' : True,
                            }
                #if currentdata:
                #    # This only works when the entity has been created
                #    postdata['baserevid'] = currentdata.get('lastrevid')

                request = self.site.simple_request(**postdata)
                try:
                    data = request.submit()
                    # Always touch the page to flush it
                    filepage.touch()
                except (pywikibot.exceptions.APIError, pywikibot.exceptions.OtherPageSaveError):
                    pywikibot.output('Got an API error while saving page. Sleeping, getting a new token and skipping')
                    # Print the offending token
                    print (token)
                    time.sleep(30)
                    # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
                    self. site.tokens.load_tokens(['csrf'])
                    # This should be a new token
                    print(self.site.tokens['csrf'])

    def addClaimJson(self, mediaid, pid, qid):
        """
        Add a claim to a mediaid

        :param mediaid: The mediaid to add it to
        :param pid: The property P id (including the P)
        :param qid: The item Q id (including the Q)
        :param summary: The summary to add in the edit
        :return: Nothing, edit in place
        """
        toclaim = {'mainsnak': { 'snaktype':'value',
                                 'property': pid,
                                 'datavalue': { 'value': { 'numeric-id': qid.replace(u'Q', u''),
                                                           'id' : qid,
                                                           },
                                                'type' : 'wikibase-entityid',
                                                }

                                 },
                   'type': 'statement',
                   'rank': 'normal',
                   }
        return [toclaim,]


def main(*args):
    fullrun = False
    alwaystouch = False
    remove3d = False
    gen = None
    genFactory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-fullrun':
            fullrun = True
        elif arg == '-alwaystouch':
            alwaystouch = True
        elif arg == '-remove3d':
            remove3d = True
        elif genFactory.handle_arg(arg):
            continue
    gen = pagegenerators.PageClassGenerator(genFactory.getCombinedGenerator(gen, preload=True))

    digitalRepresentationCleaanupBot = DigitalRepresentationCleaanupBot(gen, alwaystouch, remove3d)
    digitalRepresentationCleaanupBot.run()

if __name__ == "__main__":
    main()
