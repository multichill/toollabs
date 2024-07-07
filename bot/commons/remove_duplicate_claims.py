#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to remove duplicate claims (statements).

These are usually caused by bots doing the same edit twice on a file.
"""

import pywikibot
import hashlib
import time
import json
import gzip
from pywikibot import pagegenerators


class DuplicateClaimsBot:
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

    def run(self):
        """
        Run on the items
        """
        for filepage in self.generator:
            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.get_current_mediainfo(mediaid)

            pywikibot.output(u'Working on %s' % (filepage.title(),))

            if not filepage.exists():
                continue

            if not filepage.has_permission():
                # Picture might be protected
                continue

            self.remove_duplicate_claims(filepage, mediaid, currentdata)

    def get_current_mediainfo(self, mediaid):
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

    def remove_duplicate_claims(self, filepage, mediaid, currentdata):
        """
        Remove the duplicate claims on a single file

        :param filepage: The File to work on
        :param mediaid: Mediaid of the file
        :param currentdata: The current data on the file
        :return: None, edit in place
        """
        if not currentdata.get('statements'):
            return
        to_remove = []
        for wb_property in currentdata.get('statements'):
            statement_hashes = []
            for property_statement in currentdata.get('statements').get(wb_property):
                statement_id = property_statement.get('id')
                del property_statement['id']
                statement_json = json.dumps(property_statement, sort_keys=True).encode('utf8')
                statement_hash = hashlib.sha512(statement_json).hexdigest()
                if statement_hash in statement_hashes:
                    to_remove.append(statement_id)
                else:
                    statement_hashes.append(statement_hash)

        if len(to_remove) > 0:
            summary = 'Removing %s duplicate claims from structured data' % (len(to_remove),)

            entity_data = {'claims': []}
            for statement_id in to_remove:
                remove_claim = {'id': statement_id,
                                'remove': ''}
                entity_data['claims'].append(remove_claim)

            # Flush it
            pywikibot.output(summary)

            token = self.site.tokens['csrf']
            postdata = {'action': 'wbeditentity',
                        'format': 'json',
                        'id': mediaid,
                        'data': json.dumps(entity_data),
                        'token': token,
                        'summary': summary,
                        'bot': True,
                        'tags': 'BotSDC'
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
                print(token)
                time.sleep(30)
                # FIXME: T261050 Trying to reload tokens here, but that doesn't seem to work
                self.site.tokens.load_tokens(['csrf'])
                # This should be a new token
                print(self.site.tokens['csrf'])
        elif self.always_touch:
            try:
                filepage.touch()
            except:
                pywikibot.output('Got an API error while touching page. Sleeping, getting a new token and skipping')
                self. site.tokens.load_tokens(['csrf'])


class DuplicateClaimsDumpsBot(DuplicateClaimsBot):
    """
    Bot to remove structured data statements on Commons
    """
    def __init__(self, dump_file, always_touch):
        """
        Grab generator based on search to work on.
        """
        self.site = pywikibot.Site('commons', 'commons')
        self.site.login()
        self.site.get_tokens('csrf')
        self.repo = self.site.data_repository()
        self.full_generator = self.get_generator_from_dump(dump_file)
        self.filtered_generator = self.get_duplicates_generator(self.full_generator)
        self.always_touch = always_touch

    def get_generator_from_dump(self, dump_file):
        """
        Try to open the dump file and crash if that doesn't work

        This loads the json line by line to not load everything in memory

        :param dump_file: Name of the dump file
        :return: Generator with mediainfo
        """
        file = gzip.open(dump_file, 'rt')
        for line in file:
            if line.startswith('{'):
                json_data = json.loads(line.strip().rstrip(','))
                yield json_data

    def get_duplicates_generator(self, full_generator):
        """
        Do filter for entities that have duplicate statements in the dump
        :param full_generator:
        :return:
        """
        for entity_data in full_generator:
            if self.entity_has_duplicate_claims(entity_data):
                yield entity_data

    def entity_has_duplicate_claims(self, entity_data):
        """
        Check if an entity has duplicate claims
        :param entity_data: Data for one entity
        :return: True if duplicates, False if not
        """
        if not entity_data.get('statements'):
            return False
        for wb_property in entity_data.get('statements'):
            statement_hashes = []
            for property_statement in entity_data.get('statements').get(wb_property):
                del property_statement['id']
                statement_json = json.dumps(property_statement, sort_keys=True).encode('utf8')
                statement_hash = hash(statement_json)  # Should be faster than SHA512
                if statement_hash in statement_hashes:
                    return True
                else:
                    statement_hashes.append(statement_hash)
        return False

    def run(self):
        """
        Run on the items
        """
        for entity in self.filtered_generator:
            filepage = pywikibot.FilePage(self.site, title=entity.get('title'))

            if not filepage.exists():
                continue
            # Probably want to get this all in a preloading generator to make it faster
            mediaid = u'M%s' % (filepage.pageid,)
            currentdata = self.get_current_mediainfo(mediaid)

            pywikibot.output('Working on %s' % (filepage.title(),))

            if not filepage.exists():
                continue

            if not filepage.has_permission():
                # Picture might be protected
                continue

            self.remove_duplicate_claims(filepage, mediaid, currentdata)

def main(*args):
    always_touch = False
    gen = None
    use_dumps = False
    dump_file = '/public/dumps/public/commonswiki/entities/latest-mediainfo.json.gz'
    gen_factory = pagegenerators.GeneratorFactory()

    for arg in pywikibot.handle_args(args):
        if arg == '-alwaystouch':
            always_touch = True
        elif arg == '-usedumps':
            use_dumps = True
        elif gen_factory.handle_arg(arg):
            continue
    if use_dumps:
        duplicate_claims_bot = DuplicateClaimsDumpsBot(dump_file, always_touch)
        duplicate_claims_bot.run()
    else:
        gen = pagegenerators.PageClassGenerator(gen_factory.getCombinedGenerator(gen, preload=True))

        duplicate_claims_bot = DuplicateClaimsBot(gen, always_touch)
        duplicate_claims_bot.run()


if __name__ == "__main__":
    main()
