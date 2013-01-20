#!/usr/bin/python
# -*- coding: utf-8  -*-
'''
A bot to upload RCE images, see https://commons.wikimedia.org/wiki/Commons:Rijksdienst_voor_het_Cultureel_Erfgoed
Bot relies on data_ingestion.py in Pywikipedia

'''
import sys
sys.path.append("../pywikipedia")
import pywikibot, data_ingestion

def updateMetadata(metadata):
    '''
    Take the metadata, fix coordinates, check if it's free and add fileurl
    '''
            
    # Coordinates crap. I might end up removing them completely
    '''
    if metadata.get('Monument_monument.number.x_coordinates') and metadata.get('Monument_monument.number.y_coordinates'):
        if not (metadata.get('Monument_monument.province')==u'Noord-Holland' and metadata.get('Monument_monument.place')=='Amsterdam'):
            # Noord: 52.393
            # Zuid: 52.348247
            # West: 4.85895
            # Oost: 4.93845
            #{{{Monument_monument.place|}}}
            #{{{Monument_monument.province|}}}
            lat = float(metadata.get('Monument_monument.number.y_coordinates'))
            lon = float(metadata.get('Monument_monument.number.x_coordinates'))
            if 52.348247 < lat < 52.393 and 4.85895 < lon < 4.93845:
                # Coordinates places it in Amsterdam, but it's somewhere else
                del metadata['Monument_monument.number.x_coordinates']
                del metadata['Monument_monument.number.y_coordinates']
    '''
    if not metadata.get('Monument_monument.place'):
	metadata['Monument_monument.place'] = u'Unknown'

    # Make sure that it's free and a description is set
    if metadata.get('Rights_rights.notes')==u'http://creativecommons.org/licenses/by-sa/3.0/' and metadata.get('Reproduction_reproduction.reference') and metadata.get('Description_description'):
        metadata['fileurl'] =  'http://images.memorix.nl/rce/thumb/1200x1200/%s.jpg' % (metadata['Reproduction_reproduction.reference'],)
        return metadata

    # This image is not suitable for upload
    return False         
            
if __name__=="__main__":
    baseurl = u'http://cultureelerfgoed.adlibsoft.com/harvest/wwwopac.ashx?database=images&search=priref=%s&limit=10&output=json'
    start = 20312013
    end =   30089092
    JSONBase = [u'adlibJSON', u'recordList', u'record', 0]
    
    reader =  data_ingestion.JSONReader(baseurl, start=start, end=end, JSONBase=JSONBase, metadataFunction=updateMetadata)

    bot = data_ingestion.DataIngestionBot(reader, "%(Description_description)s - %(Monument_monument.place)s - %(priref)s - RCE.%(_ext)s", "RCE data ingestion layout", pywikibot.getSite('commons', 'commons'))
    bot.run()
