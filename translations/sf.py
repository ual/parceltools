import __main__ as ogr2osm
import logging as l
l.basicConfig(level=l.INFO, format="%(levelname)s: %(message)s")

def filterTags(attrs):
    if not attrs:
        return {}
    tags = {'area':'yes'}
    for k,v in attrs.iteritems():
        if k == u'BLKLOT':
            tags['apn'] = v
    return tags

# wrapper class for Ways.  I did this instead of overriding the base class'
# __hash__ and __eq__ functions because in other places we need the default
# versions.
class ComparableGeometry():

    def __init__(self, geometry):
        self.geometry = geometry

class ComparableWay(ComparableGeometry):

    def __hash__(self):
        return hash(tuple(self.geometry.points))

    def __eq__(self, other):
        return (self.geometry.points == other.geometry.points)

class ComparableRelation(ComparableGeometry):
    def __hash__(self):
        return hash(tuple(self.geometry.members))

    def __eq__(self, other):
        return (self.geometry.members == other.geometry.members)

def getDuplicates(items):
    dups = {}
    for i in items:
        if i in dups:
            dups[i].append(i)
        else:
            dups[i] = [i]
    return dups

def getParent(w):
    return iter(w.parents).next()

def getGrandParent(w):
    return getParent(getParent(w))

def consolidateTags(dups, features):
    ordered = sorted(dups, key=lambda d: getParent(d.geometry).tags['apn'])
    final_tags = {}
    index = 0
    for r in ordered:
        f = getParent(r.geometry)
        final_tags['apn:%d' % (index)] = f.tags['apn']
        if index != 0:
            features.remove(f)
            f.geometry.removeparent(f)
        index += 1

    tags = getParent(ordered[0].geometry).tags
    del tags['apn']
    tags.update(final_tags)

# We handle two sorts of duplicate Ways here.  One is a set of stand-alone Ways
# with parent Features that have some tags.  The other case is a set of Ways
# that have multipolygon Relation parents and Feature grandparents with tags.
def preOutputTransform(geometries, features):
    ways = [ComparableWay(w) for w in geometries if type(w) == ogr2osm.Way]

    for (way, dups) in getDuplicates(ways).items():
        if len(dups) == 1:
            continue

        l.info("Resolving " + str(len(dups)) + " duplicate ways")

        if type(getParent(way.geometry)) == ogr2osm.Relation and \
               len(way.geometry.parents) == 1 and \
               type(getGrandParent(way.geometry)) == ogr2osm.Feature:
            # If the duplicate ways belong to Relations, we assume that they
            # are pieces of multipolygons and that all of the attributes are
            # stored with the Relation.
            for w in dups[1:]:
                for p in set(w.geometry.parents):
                    p.replacejwithi(dups[0].geometry, w.geometry)

        elif type(getParent(way.geometry)) == ogr2osm.Feature and \
                 len(way.geometry.parents) == 1:
            consolidateTags(dups, features)

        else:
            # To be sure we catch anything down the line that does not fit into
            # our two simple cases, assert.
            l.error("Unsupported geometry arrangement")
            assert(False)

    relations = [ComparableRelation(r) for r in geometries if type(r) == ogr2osm.Relation]
    for (relation, dups) in getDuplicates(relations).items():
        if len(dups) == 1:
            continue
        l.info("Resolving " + str(len(dups)) + " duplicate relations")
        consolidateTags(dups, features)
