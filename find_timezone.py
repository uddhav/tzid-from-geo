__author__ = 'uddhav kambli'

import sys
import json
import datetime
import math
import csv

# Ray Intersect Segment algorithm from
# http://rosettacode.org/wiki/Ray-casting_algorithm#Python
_eps = 0.00001
_huge = sys.float_info.max
_tiny = sys.float_info.min

def ray_intersect_segment(px, py, x1, y1, x2, y2):
    ''' takes a point p=Pt() and an edge of two endpoints a,b=Pt() of a line segment returns boolean
    '''
    ax,ay,bx,by = x1,y1,x2,y2
    if ay > by:
        ax,ay,bx,by = x2,y2,x1,y1
    if py == ay or py == by:
        px,py = px, py + _eps

    intersect = False

    if (py > by or py < ay) or (
        px > max(ax, bx)):
        return False

    if px < min(ax, bx):
        intersect = True
    else:
        if abs(ax - bx) > _tiny:
            m_red = (by - ay) / float(bx - ax)
        else:
            m_red = _huge
        if abs(ax - px) > _tiny:
            m_blue = (py - ay) / float(px - ax)
        else:
            m_blue = _huge
        intersect = m_blue >= m_red
    return intersect

def _odd(x): return x%2 == 1

def is_point_inside(p, poly, ln):
    s = 0

    for i in range(ln):
        j = (i + 1) % ln

        s += ray_intersect_segment(p[1], p[0], poly[i][1], poly[i][0], poly[j][1], poly[j][0])

    return _odd(s)

# Bing Maps Tiles System
# http://msdn.microsoft.com/en-us/library/bb259689.aspx
_earthRadius = 6378137
_minLatitude = -85.05112878
_maxLatitude = 85.05112878
_minLongitude = -180
_maxLongitude = 180

# Set level of detail for the final data set
# trade-off between size and number of polygons to test
# Decides the tiles-{_level}.json
_level = 11

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

# Converts pixel XY coordinates into tile XY coordinates of the tile containing
# the specified pixel.
def _pixelXYToTileXY(pixelX, pixelY):
    return int(math.floor(pixelX / 256.0)), int(math.floor(pixelY / 256.0))

#files prepared by construct data.py
# Timezone IDs
with open('tzids.json', 'r') as data:
    tzids = json.load(data)

#    filename = 'tzids.csv'
#    outfile = open(filename, 'wb')
#    idx = 1
#
#    outfile.write("key,name\n")
#    for tzid in tzids:
#        outfile.write(str(idx) + ',"' + tzid + '"\n')
#        idx += 1
#
#    outfile.close()

# Polygons File 1
with open('polygons-1.json', 'r') as data:
    global polygons
    polygons = json.load(data)

# Polygons File 2
with open('polygons-2.json', 'r') as data:
    json_data = json.load(data)
    polygons.extend(json_data)

#idx = 1
#l = len(polygons)
#per = l / 20
#start = 0
#end = per
#i = 0
#while start != l:
#    i += 1
#    with open('polygons-' + str(i) + '.csv', 'wb') as outfile:
#        outfile.write("key,content\n")
#        for polygon in polygons[start:end]:
#            outfile.write(str(idx) + ',"' + json.dumps(polygon) + '"\n')
#            idx += 1
#
#        outfile.close()
#
#    start = end
#    end += per
#    end = min(end, l)


# Tiles of a particular detail level
# contains tiles has many polygons mapping
with open('tiles-' + str(_level) + '.json', 'r') as data:
    tiles = json.load(data)

#    filename = 'tiles.csv'
#    outfile = open(filename, 'wb')
#
#    outfile.write("key,content\n")
#    for k, v in tiles.iteritems():
#        outfile.write(str(int(k) + 1) + ',"' + json.dumps(v) + '"\n')
#
#    outfile.close()

# some locations
kentland_in = [ -87.446111, 40.769722 ]
boston_ma = [ -71.063611, 42.358056 ]
carrolton_tx = [ -96.890273, 32.953807 ]
hoover_dam = [ -114.737245, 36.016222 ]
mumbai_in = [ 72.8258, 18.9647 ]
quincy_ma = [ -71.0185, 42.2654 ]
pune_in = [ 73.8667, 18.5333 ]
border_pk = [ 70.988159, 24.717893 ]
border_in = [ 71.052704, 24.619804 ]
port_moresby = [ 151.994629, -4.512337 ]
caracas_vz = [ -66.916667, 10.5 ]
cape_canaveral = [ -80.6058589, 28.4051872 ]

# Location array
pos = [ caracas_vz, cape_canaveral, boston_ma, kentland_in, carrolton_tx, hoover_dam, mumbai_in, quincy_ma, pune_in, border_pk, border_in, port_moresby ]

# Find all timezones
for p in pos:
    # index of polygon matched
    index = 0

    now = datetime.datetime.now()

    pixelX, pixelY = _latlngToPixelXY(p[1], p[0])
    tileX, tileY = _pixelXYToTileXY(pixelX, pixelY)
    tIndex = str(tileX * (2 << _level) + tileY)


    if tIndex in tiles:
        polygon_indices = tiles[tIndex]

        np = len(polygon_indices)

        for polygon_index in polygon_indices:
            polygon = polygons[polygon_index]
            index += 1

            ln = len(polygon)

            if np == 1 or is_point_inside(p, polygon, ln):
                print('location[' + str(p) + '][' + str(index) + ']: ', tzids[polygon_index])
                print(datetime.datetime.now() - now)
                break
