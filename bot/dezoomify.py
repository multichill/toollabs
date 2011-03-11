#!/usr/bin/python
# coding=utf8
'''
TAKE A URL CONTAINING A PAGE CONTAINING A ZOOMIFY OBJECT, A ZOOMIFY BASE
DIRECTORY OR A LIST OF THESE, AND RECONSTRUCT THE FULL RESOLUTION IMAGE

License

This software is licensed under the Expat License (also called the MIT license).
Author: Inductiveload

'''

import sys, time, os
import re
import cStringIO
import urllib, urlparse
import optparse

from math import ceil, floor

try:
    import Image
except ImportError:
    print('Needs PIL to run. Exiting.')
    sys.exit()

def main():

    parser = optparse.OptionParser(usage='Usage: %prog -i <source> <options> -o <output file>')
    parser.add_option('-i', dest='url', action='store',\
                             help='the URL of a page containing a Zoomify object (unless -b or -l flags are set) (required)')
    parser.add_option('-b', dest='base', action='store_true', default=False,\
                             help='the URL is the base directory for the Zoomify tile structure' )
    parser.add_option('-l', dest='list', action='store_true', default=False,\
                             help='the URL refers to a local file containing a list of URLs or base directories to dezoomify' )
    parser.add_option('-d', dest='debug', action='store_true', default=False,\
                             help='toggle debugging information' )
    parser.add_option('-e', dest='ext', action='store', default='jpg',\
                             help='input file extension (default = jpg)' )
    parser.add_option('-q', dest='qual', action='store', default='75',\
                             help='output image quality (default=75)' )
    parser.add_option('-z', dest='zoomLevel', action='store', default=False,\
                             help='zoomlevel to grab image at (can be useful if some of a higher zoomlevel is corrupted or missing)' )
    parser.add_option('-s', dest='store', action='store_true', default=False,\
                             help='save all tiles locally' )
    parser.add_option('-o', dest='out', action='store',\
                             help='the output file for the image (required)' )

    (opts, args) = parser.parse_args()

    # check mandatory options
    if (opts.url is None):
        print("ERR: The input option '-i' must be given\n")
        parser.print_help()
        exit(-1)

    if (opts.out is None) :
        print("ERR: The output file (-o) must be given\n")
        parser.print_help()
        exit(-1)

    if (int(opts.qual) > 95) :
        print("INF: Output quality over 95% is discouraged due to large filesize without useful quality increase\n")
        cont = raw_input("Continue? [y/n] >")
        if ((cont == 'n') or (cont == 'N') ):
            exit(-1)

    Dezoomify(url=opts.url, out=opts.out, urlBase=opts.base, urlList=opts.list, debug=opts.debug, ext=opts.ext, qual=opts.qual, zoomLevel=opts.zoomLevel, store=opts.store)

def urlConcat(url1, url2):
    #simple concatenation routine for parts of urls

    if url1[-1] == '/':
        url1 = url1[0:-1]

    if url2[0] == '/':
        url2 = url2[1:]

    return url1 + '/' + url2

def getFilePath(level, col, row, ext):
    name = str(level) + '-' + str(col) + '-' + str(row) + '.' + ext
    return name

class Dezoomify():

    def getImageDirectory(self, url):
    # gets the Zoomify image base directory for the image tiles

        try:
            content = urllib.urlopen(url).read()
        except:
            print("ERR: Specified directory not found. Check the URL.")
            sys.exit()

        m = re.search('zoomifyImagePath=([^\'"&]*)[\'"&]', content)

        if not m:
            print("ERR: Source directory not found. Ensure the given URL contains a Zoomify object.")
            sys.exit()
        else:
            imagePath = m.group(1)
            print('INF: Found zoomifyImagePath: %s' % imagePath)

            netloc   = urlparse.urlparse(imagePath).netloc
            if not netloc: #the given zoomifyPath is relative from the base url

                #split the given url into parts
                parsedURL = urlparse.urlparse(url)

                # remove the last bit of path, if it has a "." (i.e. it is a file, not a directory)
                pathParts = parsedURL.path.split('/')
                m = re.search('\.', pathParts[-1])
                if m:
                    del(pathParts[-1])
                path = '/'.join(pathParts)

                # reconstruct the url with the new path, and without queries, params and fragments
                url = urlparse.urlunparse([ parsedURL.scheme, parsedURL.netloc, path, None, None, None])

                imageDir = urlConcat(url, imagePath) #add the relative url to the current url

            else: #the zoomify path is absolute
                imageDir = imagePath

            if self.debug:
                print('INF: Found image directory: ' + imageDir)
            return imageDir

    def getMaxZoom(self):
        """Construct a list of all zoomlevels with sizes in tiles"""

        zoomLevel = 0 #here, 0 is the deepest level
        width = int(ceil(self.maxWidth/float(self.tileSize))) #width of full image in tiles
        height = int(ceil(self.maxHeight/float(self.tileSize))) #height

        self.levels = []

        while True:

            self.levels.append((width, height))

            if width == 1 and height == 1:
                break
            else:
                width = int(ceil(width/2.0)) #each zoom level is a factor of two smaller
                height = int(ceil(height/2.0))

        self.levels.reverse() # make the 0th level the smallestt zoom, and higher levels, higher zoom



    def getProperties(self, imageDir, zoomLevel):
        #READ THE XML FILE AND RETRIEVE THE ZOOMIFY PROPERTIES NEEDED TO RECONSTRUCT (WIDTH, HEIGHT AND TILESIZE)
        xmlUrl = imageDir + '/ImageProperties.xml' #this file contains information about the image tiles

        content = urllib.urlopen(xmlUrl).read() #get the file's contents
        #example: <IMAGE_PROPERTIES WIDTH="2679" HEIGHT="4000" NUMTILES="241" NUMIMAGES="1" VERSION="1.8" TILESIZE="256"/>


        m = re.search('WIDTH="(\d+)"', content)
        if m:
            self.maxWidth = int(m.group(1))
        else:
            print('ERR: Width not found in ImageProperties.xml')
            sys.exit()

        m = re.search('HEIGHT="(\d+)"', content)
        if m:
            self.maxHeight = int(m.group(1))
        else:
            print('ERR: Height not found in ImageProperties.xml')
            sys.exit()

        m = re.search('TILESIZE="(\d+)"', content)
        if m:
            self.tileSize = int(m.group(1))
        else:
            print('ERR: Tile size not found in ImageProperties.xml')
            sys.exit()

        #PROCESS PROPERTIES TO GET ADDITIONAL DERIVABLE PROPERTIES

        self.getMaxZoom() #get one-indexed maximum zoom level

        self.maxZoom = len(self.levels)

        #GET THE REQUESTED ZOOMLEVEL
        if not zoomLevel: # none requested, using maximum
            self.zoomLevel = self.maxZoom-1
        else:
            zoomLevel = int(zoomLevel)
            if zoomLevel < self.maxZoom and zoomLevel >= 0:
                self.zoomLevel = zoomLevel
            else:
                self.zoomLevel = self.maxZoom-1
                if self.debug:
                    print ('ERR: the requested zoom level is not available, defaulting to maximum (%d)' % self.zoomLevel )

        #GET THE SIZE AT THE RQUESTED ZOOM LEVEL
        self.width = self.maxWidth / 2**(self.maxZoom - self.zoomLevel - 1)
        self.height = self.maxHeight / 2**(self.maxZoom - self.zoomLevel - 1)

        #GET THE NUMBER OF TILES AT THE REQUESTED ZOOM LEVEL
        self.maxxTiles = self.levels[-1][0]
        self.maxyTiles = self.levels[-1][1]

        self.xTiles = self.levels[self.zoomLevel][0]
        self.yTiles = self.levels[self.zoomLevel][1]


        if self.debug:
            print( '\tMax zoom level:    %d (working zoom level: %d)' % (self.maxZoom-1, self.zoomLevel)  )
            print( '\tWidth (overall):   %d (at given zoom level: %d)' % (self.maxWidth, self.width)  )
            print( '\tHeight (overall):  %d (at given zoom level: %d)' % (self.maxHeight, self.height ))
            print( '\tTile size:         %d' % self.tileSize )
            print( '\tWidth (in tiles):  %d (at given level: %d)' % (self.maxxTiles, self.xTiles) )
            print( '\tHeight (in tiles): %d (at given level: %d)' % (self.maxyTiles, self.yTiles) )
            print( '\tTotal tiles:       %d (to be retreived: %d)' % (self.maxxTiles * self.maxyTiles, self.xTiles * self.yTiles))


    def getTileIndex(self, level, x, y):
    #get the index of a tile in a givel level, at give coords. this is needed to get the tilegroup

        index = x + y * int(ceil( floor(self.width/pow(2, self.maxZoom - level - 1)) / self.tileSize ) )

        for i in range(1, level+1):
            index += int(ceil( floor(self.width /pow(2, self.maxZoom - i)) / self.tileSize ) ) * \
                     int(ceil( floor(self.height/pow(2, self.maxZoom - i)) / self.tileSize ) )

        return index


    def constructBlankImage(self):
        try:
            self.image = Image.new('RGB', (self.width, self.height), "#000000")
        except MemoryError:
            print "ERR: Image too large to fit into memory. Exiting"
            sys.exit(2)
        return

    def blankTile(self):
        return Image.new('RGB', (self.tileSize, self.tileSize), "#000000")


    def addTiles(self, imageDir):
        for col in range(self.xTiles):
            for row in range(self.yTiles):

                tileIndex = self.getTileIndex(self.zoomLevel, col, row)
                tileGroup = tileIndex // 256

                if self.debug:
                    print("\tINF: Getting image number (row, col): " + str(row).rjust(2) +', ' + str(col).rjust(2)  + ': Index: '+ str(tileIndex).rjust(3) + ', Tilegroup: %d'% tileGroup)

                filepath = getFilePath(self.zoomLevel, col, row, self.ext) #construct the filename (zero indexed level)
                url = imageDir + '/' + 'TileGroup%d'%tileGroup + '/' + filepath

                while True: #loop to protect against a dropped connection
                    try:
                        tileFile = urllib.urlopen(url)
                        break
                    except:
                        time.sleep(0.2) #wait a moment
                        if self.debug:
                            print "INF: Failed to retreive tile: retrying."

                #construct the image using the data.
                try:
                    imageData = cStringIO.StringIO(tileFile.read()) # constructs a StringIO holding the image
                    tile = Image.open(imageData)
                except IOError: #failure to read the image tile
                    if self.debug:
                        print ('\t\tERR: Tile not found or corrupted, skipping. HTTP code:%d' % (tileFile.code))
                    tile = self.blankTile() #make a blank tile instead

                if self.store:
                    tile.save(os.path.join(self.store , filepath), quality=int(self.qual) ) #save the tile

                self.image.paste(tile, (self.tileSize*col, self.tileSize*row)) #paste into position


    def getUrls(self, url, urlBase, urlList): #returns a list of base URLs for the given Dezoomify object(s)
        if not urlList: #if we are dealing with a single object
            if not urlBase:
                self.imageDirs = [ self.getImageDirectory(url) ]  # locate the base directory of the zoomify tile images
            else:
                self.imageDirs = [ url ]         # it was given directly

        else: #if we are dealing with a file with a list of objects
            listFile = open( url, 'r')
            imageDirs = [] #empty list of directories

            for line in listFile:
                if not urlBase:
                    self.imageDirs = [ self.getImageDirectory(line) ]  # locate the base directory of the zoomify tile images
                else:
                    self.imageDirs = [ line ]         # it was given directly


    def setupDirectory(self):
        # if we will save the tiles, set up the directory to save in
        if self.store:
            root, ext = os.path.splitext(self.out)

            if not os.path.exists(root):
                if self.debug:
                    print( 'INF: Creating image storage directory: %s' % root)
                os.mkdir(root)
            self.store = root
        else:
            self.store = False



    def __init__(self, url, out, urlBase=False, urlList=False, debug=False, ext=u'jpg', qual='75', zoomLevel=False, store=False):
        self.url = url
        self.out = out
        self.urlBase = urlBase
        self.urlList = urlList
        self.debug = debug
        self.ext = ext
        self.qual = qual
        self.zoomLevel = zoomLevel
        self.store = store

        self.setupDirectory()
        self.getUrls(self.url, self.urlBase, self.urlList)

        i = 0
        for imageDir in self.imageDirs:

            self.getProperties(imageDir, self.zoomLevel)       # inspect the ImageProperties.xml file to get properties, and derive the rest

            self.constructBlankImage() # create the blank image to fill with tiles
            self.addTiles(imageDir)            # find, download and paste tiles into place

            if self.urlList: #add a suffix to the output file names if needed
                root, ext = os.path.splitext(self.out)
                destination = root + '%03d' % i + ext
            else:
                destination = self.out
            
            self.image.save(destination, quality=int(self.qual) ) #save the dezoomified file

            if self.debug:
                print( 'INF: Dezoomifed image created and saved to ' + destination )

            i += 1

if __name__ == "__main__":
    try:
        main()
    finally:
        None
