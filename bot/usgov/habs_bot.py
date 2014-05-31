#!/usr/bin/python
# -*- coding: utf-8  -*-
'''

Bot to upload images from the Historic American Buildings Survey

'''
import urllib, re, json
import sys
import pywikibot, data_ingestion

def HABSReader(start=1, end=20000):
    '''
    Loops over search pages at the Library of Congress and than loops of the items.
    For each item get the metadata from JSON and update the metadata
    Yields photo objects
    '''
    searchurl = u'http://www.loc.gov/pictures/search/?sp=%s&co=hh&st=list&fo=json'
    for i in range(start, end):
        JSONPage = urllib.urlopen(searchurl % (i,))
        JSONData = json.load(JSONPage)
        JSONPage.close()
        if JSONData.get(u'results'):
            for result in JSONData.get(u'results'):
                url = result.get(u'links').get(u'item') + u'?fo=json'
                photo = data_ingestion.processJSONPage(url, metadataFunction=updateMetadata)
                if photo:
                    yield photo


def updateMetadata(metadata):
    '''
    Check the metadata and extract some fields
    '''
    # Try to find the highest resolution tiff or fail. Largest seems to be always empty
    if metadata.get(u'resources_largest') and metadata.get(u'resources_largest').endswith(u'.tif'):
        metadata['fileurl'] = metadata.get(u'resources_largest')
    elif metadata.get(u'resources_larger') and metadata.get(u'resources_larger').endswith(u'.tif'):
        metadata['fileurl'] = metadata.get(u'resources_larger')
    else:
        # No tiff found, fail
        return False

    # Get the loc_id used in the source template
    if metadata.get(u'item_resource_links') and metadata.get(u'item_resource_links').startswith(u'http://hdl.loc.gov/loc.pnp/'):
        metadata['loc_id'] = metadata.get(u'item_resource_links').replace(u'http://hdl.loc.gov/loc.pnp/', u'')
    else:
        # No valid id found, fail
        return False

    # reproductions contains a lot of html cruft
    if metadata.get(u'reproductions'):
        del metadata['reproductions']

    # Try to get the county and the state from the title (it's at the end)
    match=re.match(u'^.*,(?P<county>[^,]+),(?P<state>[^,]+)', metadata['item_title'], re.DOTALL)
    if match:
	metadata[u'county'] = match.group(u'county').strip()
	metadata[u'state'] = match.group(u'state').strip()

    # Blacklist some images
    # FIXME: Do something with fancy regexes
    blacklist = [u'Photocopy',
		 u'Historic Society',
		 ]
    for blitem in blacklist:
	if blitem in metadata['item_title']:
	    pywikibot.output(u'Found a blacklisted word in the title: "%s"' % blitem)
	    return False

    return metadata

def main(args):
    '''
    Main loop.
    '''
    start_id = 3
    end_id = 18473
    single_id = 0

    site = pywikibot.getSite('commons', 'commons')


    for arg in pywikibot.handleArgs():
        if arg.startswith('-start_id'):
            if len(arg) == 9:
                start_id = pywikibot.input(u'What is the id of the search page you want to start at?')
            else:
                start_id = arg[10:]
        elif arg.startswith('-end_id'):
            if len(arg) == 7:
                end_id = pywikibot.input(u'What is the id of the search page you want to end at?')
            else:
                end_id = arg[8:]
	elif arg.startswith('-id'):
	    if len(arg) == 3:
		single_id = pywikibot.input(u'What is the id of the search page you want to transfer?')
	    else:
		single_id = arg[4:]

    if single_id > 0:
        start_id = single_id
        end_id = int(single_id) + 1

    reader =  HABSReader(start=int(start_id), end=int(end_id))
    bot = data_ingestion.DataIngestionBot(reader, "%(item_title)s - LOC - %(resources_id)s.%(_ext)s", "HABS data ingestion layout", pywikibot.getSite('commons', 'commons'))
    bot.run()
         
if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    finally:
        print u'All done'
