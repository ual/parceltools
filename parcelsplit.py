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

    def get_blocknum(f):

        if not f.GetField(options.blocknum):
            return None

        if options.prefix_len:
            return eval('f.GetField(options.blocknum)[0:%d]' % options.prefix_len)

        return f.GetField(options.blocknum)

    if options.index:
        l.info('Creating index...')
        src.ExecuteSQL('CREATE INDEX ON ' + layer.GetName() + ' USING ' + options.blocknum)

    total = layer.GetFeatureCount()
    l.info('Reading %d features...' % total)
    blocknums = set()
    features = [layer.GetNextFeature() for i in range(layer.GetFeatureCount())]

    # If a prefix length was specified, we need to know how long the suffix is.
    fill = None
    if options.prefix_len:
        full_blocknums = [len(f.GetField(options.blocknum)) for f in features if f.GetField(options.blocknum)]
        min_len = min(full_blocknums)
        max_len = min(full_blocknums)
        if min_len != max_len:
            l.warning("IDs vary from %d to %d and I (wrongly) assume that they are all %d" % \
                      (min_len, max_len, min_len))
        fill = min_len - options.prefix_len
    features = [get_blocknum(f) for f in features]
    blocknums = sorted([x for x in features if x not in blocknums and not blocknums.add(x)])

    def get_query(b):
        if options.prefix_len:
            return options.blocknum + ' IS NOT NULL AND ' + \
                   options.blocknum + ' >= ' + b + fill*'0' + ' AND ' + \
                   options.blocknum + ' <= ' + b + fill*'9'
        return options.blocknum + '=' + b

    dest = create_dest(options.outdir, 0, layer)
    dlayer = dest.GetLayerByIndex(0)
    i = 0
    count = 0
    for b in blocknums:
        if b:
            layer.SetAttributeFilter(get_query(b))
        else:
            layer.SetAttributeFilter(options.blocknum + ' IS NULL')
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
        count += layer.GetFeatureCount()

    if dlayer.GetFeatureCount() == 0:
        n = dest.name
        dest.Destroy()
        ogr.GetDriverByName('ESRI Shapefile').DeleteDataSource(n)
    else:
        l.info('Wrote ' + str(dlayer.GetFeatureCount()) + ' to ' + dest.name)
        dest.Destroy()

    if count != total:
        l.warning("Read %d total features but wrote %d." % (total, count))

def _sort_one_pass(features):
    sorted = {}
    total = len(features)
    count = 0
    while True:
        if len(features) == 0:
            break
        count += 1
        current_key = features.keys()[0]
        current = features.pop(current_key)
        sys.stdout.write("\r%f%%" % (count*100.0/total,))
        sys.stdout.flush()
        for key in sorted.keys():
            if current_key.Touches(key):
                new_key = key.Union(current_key)
                sorted[new_key] = sorted[key] + current
                del(sorted[key])
                current = None
                break

        # we checked all of the sorted blocks to no avail.  Create a new sorted
        # group.
        if current:
            sorted[current_key] = current
    return sorted

def divide_by_touching(layer, options):

    if options.index:
        l.info('Creating index...')
        src.ExecuteSQL('CREATE SPATIAL INDEX ON ' + layer.GetName())

    # Sort the polygons by whether or not they touch
    l.info('Reading features...')

    # Start with each feature in its own list
    features = [[layer.GetNextFeature()] for i in range(layer.GetFeatureCount())]
    geometries = [f[0].GetGeometryRef() for f in features]
    features = dict(zip(geometries, features))
    l.info('Sorting features...')
    previous_len = -1
    count = 0
    while len(features) != previous_len:
        l.info('\titeration %d...' % count)
        previous_len = len(features)
        features = _sort_one_pass(features)
        count += 1

    sys.stdout.write("\n")
    l.info('Sorted %d features into %d groups' % (layer.GetFeatureCount(), len(features)))

    dest = create_dest(options.outdir, 0, layer)
    dlayer = dest.GetLayerByIndex(0)
    i = 0
    for key, group in features.iteritems():

        if dlayer.GetFeatureCount() > 0 and \
           (len(group) + dlayer.GetFeatureCount() > options.max_features or \
            len(group) > options.max_features):
            l.info('Wrote ' + str(dlayer.GetFeatureCount()) + ' to ' + dest.name)
            dest.Destroy()
            i += 1
            dest = create_dest(options.outdir, i, layer)
            dlayer = dest.GetLayerByIndex(0)

        if len(group) > options.max_features:
            l.warning('exceeded max features')
        [dlayer.CreateFeature(f) for f in group]

    if dlayer.GetFeatureCount() == 0:
        n = dest.name
        dest.Destroy()
        ogr.GetDriverByName('ESRI Shapefile').DeleteDataSource(n)
    else:
        l.info('Wrote ' + str(dlayer.GetFeatureCount()) + ' to ' + dest.name)
        dest.Destroy()

if __name__ == "__main__":
    usage = "usage: %prog [OPTIONS] <shpfile>"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('-l', '--layer', dest='layer',
                      help='''Layer in the shpfile to split.''')
    parser.add_option('-b', '--block-number-attribute', dest='blocknum',
                      help='''Attribute that contains the block number''')
    parser.add_option('-i', '--index', dest='index', action="store_true",
                      help='''Create an index to speed up processing''')
    parser.add_option('-m', '--max-features', dest='max_features', default=1000,
                      help='''Maximum features per chunk (Defaults to 1000)''', type=int)
    parser.add_option('-o', '--output-directory', dest='outdir', default='.',
                      help='''Output directory for chunks''')
    parser.add_option('-p', '--prefix-length', dest='prefix_len', type=int,
                      help='''Length of the block number.  If this is unspecified,
                              The entire attribute specified by -b is assumed to be
                              the block number.  Otherwise, the attribute is truncated
                              to the length specified by -p.''')

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

