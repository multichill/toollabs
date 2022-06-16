#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to add missing property constraints to Wikidata property to identify artworks

See for example https://www.wikidata.org/wiki/Property:P350

It will check if all the constraints are present and if not, add it.

"""

import pywikibot
from pywikibot import pagegenerators
import pywikibot.data.sparql

class ArtworkPropertyConstraintBot:
    """
    A bot to add gender to people
    """
    def __init__(self, dryrun=False):
        """
        Arguments:
            * wdprop    - The Wikidata property to work on
        """
        self.dryrun = dryrun
        self.repo = pywikibot.Site().data_repository()
        self.generator = self.get_artwork_properties_generator()

        self.requires_properties = {'P170': 'normal',  # creator (P170)
                                    'P571': 'normal',  # inception (P571)
                                    'P195': 'normal',  # collection (P195)
                                    'P217': 'normal',  # inventory number (P217)
                                    'P276': 'normal',  # location (P276)
                                    'P186': 'suggestion',  # made from material (P186)
                                    'P136': 'suggestion',  # genre (P136)
                                    'P180': 'suggestion',  # depicts (P180)
                                    'P2048': 'suggestion',  # height (P2048)
                                    'P2049': 'suggestion',  # width (P2049)
                                    'P6216': 'suggestion',  # copyright status (P6216)
                                    }

    def get_artwork_properties_generator(self):
        """
        Generator that yields the properties to work on
        :return:
        """
        query = """SELECT ?item WHERE {
  ?item wikibase:directClaim ?propertyclaim ;
            wikibase:propertyType wikibase:ExternalId ;
            wdt:P31 wd:Q44847669 .
  }"""
        return pagegenerators.PreloadingEntityGenerator(pagegenerators.WikidataSPARQLPageGenerator(query, site=self.repo))

    def run(self):
        """
        Starts the robot.
        """
        for artwork_property in self.generator:
            self.process_property(artwork_property)

    def process_property(self, artwork_property):
        """
        Process a single artwork property for constraints
        :param artwork_property: The property to work on
        :return: Nothing, edit in place
        """
        pywikibot.output('Working on property %s' % (artwork_property.title(),))
        data = artwork_property.get()
        claims = data.get('claims')

        if not 'P2302' in claims:
            # If no constraints have been set up, just return
            return

        found_constraints = []
        found_requires_properties = []

        for constraint in claims.get('P2302'):
            constraint_qid = constraint.getTarget().title()
            found_constraints.append(constraint_qid)
            if constraint_qid=='Q21503247': # item-requires-statement constraint
                if constraint.qualifiers.get('P2306'):
                    requires_property = constraint.qualifiers.get('P2306')[0].getTarget()
                    found_requires_properties.append(requires_property.title(with_ns=False))

        # Check for the common constraints
        if 'Q21502404' not in found_constraints:
            # Just add the format constraint, adding the actual regex is manual and should be rare to hit this
            self.add_constraint(artwork_property, 'Q21502404')
        if 'Q19474404' not in found_constraints and 'Q52060874' not in found_constraints:
            # single-value or single-best-value constraint should be on it
            self.add_constraint(artwork_property, 'Q19474404')
        if 'Q21502410' not in found_constraints:
            # distinct-values constraint should be on it
            self.add_constraint(artwork_property, 'Q21502410')
        if 'Q21503250' not in found_constraints:
            # type constraint should be on it. Use work of art (Q838948) as the class
            qualifiers = [('P2308', 'Q838948'), ('P2309', 'Q21503252'), ]
            self.add_constraint(artwork_property, 'Q21503250', qualifiers)
        if 'Q52004125' not in found_constraints:
            # allowed-entity-types should be on it. Use Wikibase item (Q29934200)
            qualifiers = [('P2305', 'Q29934200'), ]
            self.add_constraint(artwork_property, 'Q52004125', qualifiers)
        if 'Q53869507' not in found_constraints:
            # property scope constraint should be on it. Use  as main value (Q54828448) &  as reference (Q54828450)
            qualifiers = [('P5314', 'Q54828448'), ('P5314', 'Q54828450'), ]
            self.add_constraint(artwork_property, 'Q53869507', qualifiers)

        # label in language constraint (Q108139345) can't really be added by a bot yet

        for required_property in self.requires_properties:
            if required_property not in found_requires_properties:
                constraint_status = self.requires_properties.get(required_property)
                qualifiers = [('P2306', required_property), ]
                if constraint_status=='suggestion':
                    qualifiers.append(('P2316', 'Q62026391'))
                self.add_constraint(artwork_property, 'Q21503247', qualifiers)

        return

    def add_constraint(self, artwork_property, constraint_qid, qualifiers=[]):
        """
        Function to add a constraint
        :param artwork_property: The property to add the constraint to
        :param constraint_qid: The Wikidata item for the constraint
        :param qualifiers: A list of property and qid tuples
        :return: Add the new constraint in place
        """
        pywikibot.output('Adding %s with %s to %s' % (constraint_qid, qualifiers, artwork_property.title()))
        summary = '[[Wikidata:WikiProject sum of all paintings/External identifiers|adding missing constrains to external identifiers]]'

        if self.dryrun:
            return
        pid = 'P2302'
        new_claim = pywikibot.Claim(self.repo, pid)
        dest_item = pywikibot.ItemPage(self.repo, constraint_qid)
        new_claim.setTarget(dest_item)
        artwork_property.addClaim(new_claim, summary=summary)

        for (qualifier_property, qualifier_target_id) in qualifiers:
            new_qualifier = pywikibot.Claim(self.repo, qualifier_property)
            # Target of the qualifier can be an item or a property
            if qualifier_target_id.startswith('Q'):
                qualifier_target = pywikibot.ItemPage(self.repo, qualifier_target_id)
            elif qualifier_target_id.startswith('P'):
                qualifier_target = pywikibot.PropertyPage(self.repo, qualifier_target_id)
            # If bogus data
            if qualifier_target:
                new_qualifier.setTarget(qualifier_target)
                new_claim.addQualifier(new_qualifier, summary=summary)


def main(*args):
    dryrun = False

    for arg in pywikibot.handle_args(args):
        if arg.startswith('-dry'):
            dryrun = True

    artwork_property_constraint_bot = ArtworkPropertyConstraintBot(dryrun=dryrun)
    artwork_property_constraint_bot.run()


if __name__ == "__main__":
    main()
