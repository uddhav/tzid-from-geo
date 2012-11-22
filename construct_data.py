__author__ = 'uddhav kambli'

import json
import math
from shapely.geometry import Polygon
from shapely.geometry import box
from shapely import speedups
from datetime import datetime

if speedups.available:
    speedups.enable()

# Bing Maps Tiles System
# http://msdn.microsoft.com/en-us/library/bb259689.aspx
_earthRadius = 6378137
_minLatitude = -85.05112878
_maxLatitude = 85.05112878
_minLongitude = -180
_maxLongitude = 180

# Set level of detail for the final data set
# trade-off between size and number of polygons to test
_level = 10

# Clips a number to the specified minimum and maximum values.
def _clip(num, minValue, maxValue):
    return min(max(num, minValue), maxValue)

# Converts a point from latitude/longitude WGS-84 coordinates (in degrees)
# into pixel XY coordinates at a specified level of detail.
def _latlngToPixelXY(lat, lng):
    latitude = _clip(lat, _minLatitude, _maxLatitude)
    longitude = _clip(lng, _minLongitude, _maxLongitude)

    x = (longitude + 180) / 360.0
    sinLatitude = math.sin(latitude * math.pi / 180.0)
    y = 0.5 - math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * math.pi)

    mapSize = 256 << _level
    pixelX = int(_clip(x * mapSize + 0.5, 0, mapSize - 1))
    pixelY = int(_clip(y * mapSize + 0.5, 0, mapSize - 1))

    return pixelX, pixelY

# GEOJson point
def _latlngTupleToPixelXY(latlng):
    return tuple(_latlngToPixelXY(latlng[1], latlng[0]))

# Converts pixel XY coordinates into tile XY coordinates of the tile containing
# the specified pixel.
def _pixelXYToTileXY(pixelX, pixelY):
    return int(math.floor(pixelX / 256.0)), int(math.floor(pixelY / 256.0))

# Converts a pixel from pixel XY coordinates at a specified level of detail
# into latitude/longitude WGS-84 coordinates (in degrees).
def _pixelXYToLatlng(pixelX, pixelY):
    mapSize = 256 << _level
    x = (_clip(pixelX, 0, mapSize - 1) / mapSize) - 0.5
    y = 0.5 - (_clip(pixelY, 0, mapSize - 1) / mapSize)

    latitude = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
    longitude = 360 * x

    return latitude, longitude

# Bounding box for bing maps tile
def _boxForTile(tx, ty):
    x0 = tx << 8
    y0 = ty << 8
    x1 = x0 + 256
    y1 = y0 + 256

    return x0, y0, x1, y1

# Convert GEOJson Polygon to VE Pixel Polygon
def _polygonInVEPixel(polygon):
    ve_polygon = []

    for point in polygon:
        vex, vey = _latlngToPixelXY(point[1], point[0])
        ve_polygon.append([ vex, vey ])

    return ve_polygon

# test intersection of polygon and box
def _testXY(x, y):
    x0, y0, x1, y1 = _boxForTile(x, y)
    b = box(x0, y0, x1, y1)

    return polygon_obj.intersects(b)

# Files from http://efele.net/maps/tz/world/
# converted by http://converter.mygeodata.eu/
# That was quick!
with open('data.json') as data:
    json_data = json.load(data)

    features = json_data['features']

    # Final tiles data
    zones = {}

    # Bing Map Size for level
    size = 2 << _level

    # Max number of polygons per tile
    # May be avg is the better metric
    # I found Level 11 to be optimal
    # but 10 or 9 are not bad
    max_z = 0

    # Polygon index
    c = 0

    # Number of polygons
    l = len(features)

#    lookup_table = []
#    ids = set()

    tzs = []
    polys = []

    total_now = datetime.now()

    for feature in features:
        tzid = feature['properties']['TZID']
        polygon = feature['geometry']['coordinates'][0]

        print('Analyzing polygon ' + str(c + 1) + ' of ' + str(l))

        polygon_now = datetime.now()

        d = 0

        # Not interested in oceans and uninhabited areas
        # This can be easily augmented but no benefit for this hackathon
        if tzid is not None and tzid != 'uninhabited' and polygon is not None:
            polygon_obj = Polygon([ _latlngTupleToPixelXY(point) for point in polygon])
            minx, miny, maxx, maxy = polygon_obj.bounds

            # Get bounding box of polygon
            # break it into tile boxes of size decided by the level
            tileMinX, tileMinY = _pixelXYToTileXY(minx, miny)
            tileMaxX, tileMaxY = _pixelXYToTileXY(maxx, maxy)

            # Spiral inward through the 2D tiles in polygon bounds array
            # if we end a loop without any intersection then continue
            # otherwise all the tiles further in are also within the polygon
            # This is an optimization that may cause false matches but I found
            # a few at level 9, 10, 11, at 12 I found 23 false tiles. It will probably
            # go up for higher levels. It's worth the speedup. For more accurate
            # calculation uncomment below
            X = tileMaxX - tileMinX + 1
            Y = tileMaxY - tileMinY + 1

            print('   Tiles Matrix = ' + str(X) + 'x' + str(Y))

            x_upper = tileMaxX + 1
            x_lower = tileMinX
            y_upper = tileMaxY + 1
            y_lower = tileMinY

            dx = 0
            dy = 1

            x = x_lower
            y = y_lower

            n = X * Y
            m = 0

            all = False
            test_all = False

            while m < n:
                if dy == 1:
                    all = test_all

                    if all:
                        break

                    test_all = True

                    while y < y_upper:
                        m += 1
#                        print(x, y, 'dy == 1')
                        if all or _testXY(x, y):
                            d += 1

                            index = x * size + y

                            if index in zones:
                                zones[index].append(c)
                                max_z = max(max_z, len(zones[index]))

                            else:
                                zones[index] =  [ c ]
                        else:
                            test_all = False

                        y += 1

                    y_upper -= 1
                    y = y_upper
                    x += 1

                    dy = 0
                    dx = 1

                elif dx == 1:
                    while x < x_upper:
                        m += 1
#                        print(x, y, 'dx == 1')
                        if all or _testXY(x, y):
                            d += 1

                            index = x * size + y

                            if index in zones:
                                zones[index].append(c)
                                max_z = max(max_z, len(zones[index]))

                            else:
                                zones[index] =  [ c ]
                        else:
                            test_all = False

                        x += 1

                    x_upper -= 1
                    x = x_upper
                    y -= 1

                    dx = 0
                    dy = -1

                elif dy == -1:
                    while y >= y_lower:
                        m += 1
#                        print(x, y, 'dy == -1')
                        if all or _testXY(x, y):
                            d += 1

                            index = x * size + y

                            if index in zones:
                                zones[index].append(c)
                                max_z = max(max_z, len(zones[index]))

                            else:
                                zones[index] =  [ c ]
                        else:
                            test_all = False

                        y -= 1

                    x -= 1
                    x_lower += 1
                    y = y_lower

                    dy = 0
                    dx = -1

                else:
                    while x >= x_lower:
                        m += 1
#                        print(x, y, 'dx == -1')
                        if all or _testXY(x, y):
                            d += 1

                            index = x * size + y

                            if index in zones:
                                zones[index].append(c)
                                max_z = max(max_z, len(zones[index]))

                            else:
                                zones[index] =  [ c ]
                        else:
                            test_all = False

                        x -= 1

                    x = x_lower
                    y_lower += 1
                    y = y_lower

                    dx = 0
                    dy = 1

            if m < n:
                print('   Found chunk! = ' + str(x_upper - x_lower) + 'x' + str(y_upper - y_lower))
                for i in xrange(x_lower, x_upper):
                    for j in xrange(y_lower, y_upper):
                        index = i * size + j
                        d += 1

                        if index in zones:
                            zones[index].append(c)
                            max_z = max(max_z, len(zones[index]))

                        else:
                            zones[index] =  [ c ]

             # Fool proof way to check polygons in tiles
#            for i in range(tileMinX, tileMaxX + 1):
#                for j in range(tileMinY, tileMaxY + 1):
#                    if i < size and j < size:
#                        x0, y0, x1, y1 = _boxForTile(i, j)
#                        b = box(x0, y0, x1, y1)
#
#                        if polygon_obj.intersects(b):
#                            index = i * size + j
#                            d += 1
#
#                            if index in zones:
#                                zones[index].append(c)
#                                max_z = max(max_z, len(zones[index]))
#
#                            else:
#                                zones[index] =  [ c ]

            print('   Took ' + str(datetime.now() - polygon_now))
            print('   Detected = ' + str(d) + ' tiles')

#        lookup_table.append([tzid, polygon])
#        if d > 1:
#            polys.append(polygon)
#        else:
#            polys.append([])
        polys.append(polygon)
        tzs.append(tzid)
        c += 1

    print('Total time: ' + str(datetime.now() - total_now))
    print('End Length + Max polygons per tile')
    print(len(zones), max_z)

#    result = { 'polygons' : lookup_table, 'tiles' : zones }
#
#    # File
#    filename = 'zones-len-' + str(len(zones)) + '-max-' + str(max_z) + '-level-' + str(_level) + '.json'
#    print('Writing to ' + filename)
#    final_data = json.dumps(result)
#    outfile = open(filename, 'w')
#    outfile.write(final_data)
#    outfile.close()

#    File
    filename = 'tzids.json'
    print('Writing to ' + filename)
    final_data = json.dumps(tzs)
    outfile = open(filename, 'wb')
    outfile.write(final_data)
    outfile.close()

#    File
    filename = 'polygons-1.json'
    print('Writing to ' + filename)
    ln = len(polys) / 2
    final_data = json.dumps(polys[:ln])
    outfile = open(filename, 'wb')
    outfile.write(final_data)
    outfile.close()

    filename = 'polygons-2.json'
    print('Writing to ' + filename)
    final_data = json.dumps(polys[ln:])
    outfile = open(filename, 'wb')
    outfile.write(final_data)
    outfile.close()

    # File
    filename = 'tiles-' + str(_level) + '.json'
    print('Writing to ' + filename)
    final_data = json.dumps(zones)
    outfile = open(filename, 'wb')
    outfile.write(final_data)
    outfile.close()



