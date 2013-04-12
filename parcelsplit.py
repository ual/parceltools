#!/usr/bin/env python

'''parcelsplit.py

Read in a shapefile of parcels and output many smaller ones that are easier to
process.  Say parcelsplit.py -h for more details.

Copyright (c) 2013 Urban Analytics Lab, U.C. Berkeley
Brian Cavagnolo <bcavagnolo@berkeley.edu>

LICENSE: http://opensource.org/licenses/mit-license.
'''

import logging as l
l.basicConfig(level=l.INFO, format="%(levelname)s: %(message)s")

import sys
from osgeo import ogr
import os
import optparse

# Create a data source with a single layer that has the same properties as the
# specified layer.
#
# TODO: The fiona API for ogr has a more succinct way to do this:
# http://gis.stackexchange.com/questions/56703/better-way-to-duplicate-a-layer-using-ogr-in-python
# I'm not sure if filtering records by attribute is as fast as ogr, or if
# there's a way to get at that feature under the hood.
def create_dest(outdir, i, layer):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dest = os.path.join(outdir, '%s_%04d.shp' % (layer.GetName(), i))
    if os.path.exists(dest):
        driver.DeleteDataSource(dest)
    dest_lname = '%s_%04d' % (layer.GetName(), i)
    ds = driver.CreateDataSource(dest)
    dest_layer = ds.CreateLayer(dest_lname,
                                srs = layer.GetSpatialRef(),
                                geom_type=layer.GetLayerDefn().GetGeomType())
    feature  = layer.GetFeature(0)
    [dest_layer.CreateField(feature.GetFieldDefnRef(i)) for i in range(feature.GetFieldCount())]
    return ds

def divide_by_blocknum(layer, options):
    if options.index:
        l.info('Creating index...')
        src.ExecuteSQL('CREATE INDEX ON ' + layer.GetName() + ' USING ' + options.blocknum)

    l.info('Reading features...')
    blocknums = set()
    features = [layer.GetNextFeature().GetField(options.blocknum) for i in range(layer.GetFeatureCount())]
    blocknums = sorted([x for x in features if x not in blocknums and not blocknums.add(x)])

    dest = create_dest(options.outdir, 0, layer)
    dlayer = dest.GetLayerByIndex(0)
    i = 0
    for b in blocknums:
        layer.SetAttributeFilter(options.blocknum + '=' + b)

        if dlayer.GetFeatureCount() > 0 and \
           (layer.GetFeatureCount() + dlayer.GetFeatureCount() > options.max_features or \
            layer.GetFeatureCount() > options.max_features):
            l.info('Wrote ' + str(dlayer.GetFeatureCount()) + ' to ' + dest.name)
            dest.Destroy()
            i += 1
            dest = create_dest(options.outdir, i, layer)
            dlayer = dest.GetLayerByIndex(0)

        if layer.GetFeatureCount() > options.max_features:
            l.warning('Block ' + b + ' has ' + str(layer.GetFeatureCount()) +
                      ' features but the max is ' + str(options.max_features))

        [dlayer.CreateFeature(layer.GetNextFeature()) for f in range(layer.GetFeatureCount())]

    if dlayer.GetFeatureCount() == 0:
        n = dest.name
        dest.Destroy()
        ogr.GetDriverByName('ESRI Shapefile').DeleteDataSource(n)
    else:
        l.info('Wrote ' + str(dlayer.GetFeatureCount()) + ' to ' + dest.name)
        dest.Destroy()

def divide_by_touching(layer, options):
    # Sort the polygons by whether or not they touch
    l.info('Reading features...')
    features = set([layer.GetNextFeature() for i in range(layer.GetFeatureCount())])
    sorted = []
    count = 0
    l.info('Sorting features...')
    while True:
        if len(features) == 0:
            break
        current = features.pop()
        sys.stdout.write("\r%f%%" % (count*100.0/layer.GetFeatureCount(),))
        sys.stdout.flush()
        for group in sorted:
            for member in group:
                if current.GetGeometryRef().Touches(member.GetGeometryRef()):
                    group.append(current)
                    count += 1
                    current = None
                    break
            if not current:
                break
        # we checked all of the sorted blocks to no avail.  Create a new sorted
        # group.
        if current:
            sorted.append([current])
            count += 1

    l.info('Sorted %d features into %d groups' % (layer.GetFeatureCount(), len(sorted)))

if __name__ == "__main__":
    usage = "usage: %prog [OPTIONS] <shpfile>"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('-l', '--layer', dest='layer',
                      help='''Layer in the shpfile to split.''')
    parser.add_option('-b', '--block-number-attribute', dest='blocknum',
                      help='''Attribute that represents the block number''')
    parser.add_option('-i', '--index', dest='index',
                      help='''Create an index to speed up processing''')
    parser.add_option('-m', '--max-features', dest='max_features', default=1000,
                      help='''Maximum features per chunk (Defaults to 1000)''')
    parser.add_option('-o', '--output-directory', dest='outdir', default='.',
                      help='''Output directory for chunks''')

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("Please specify a single shapefile.")

    shpfile = args[0]
    src = ogr.Open(shpfile, 0)
    if src is None:
        l.error('Failed to open ' + shpfile)
        sys.exit(1)

    if not options.layer and src.GetLayerCount() == 1:
        layer = src.GetLayerByIndex(0)
    elif options.layer:
        layer = src.GetLayerByName(options.layer)
        if not layer:
            l.error('Layer "' + options.layer + '" does not exist.')
            l.error('Options are: ' +
                    ','.join([src.GetLayerByIndex(i).GetName() for i in range(src.GetLayerCount())]))
            sys.exit(1)
    else:
        layer_names = [src.GetLayerByIndex(i).GetName() for i in range(src.GetLayerCount())]
        l.error('Please specify a layer\n (Options include ' +
                ','.join(layer_names) + ')')
        sys.exit(1)

    if not os.path.exists(options.outdir):
        os.mkdir(options.outdir)
    options.outdir = os.path.abspath(options.outdir)

    if options.blocknum:
        divide_by_blocknum(layer, options)
    else:
        divide_by_touching(layer, options)

