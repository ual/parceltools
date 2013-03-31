import __main__ as ogr2osm
import logging as l
l.basicConfig(level=l.INFO, format="%(levelname)s: %(message)s")

def filterTags(attrs):
    if not attrs:
        return {}
    tags = {'landuse':'unknown'}
    for k,v in attrs.iteritems():
        if k == u'BLKLOT':
            tags['apn'] = v
    return tags

# wrapper class for Ways.  I did this instead of overriding the base class'
# __hash__ and __eq__ functions because in other places we need the default
# versions.
class ComparableWay():
    def __init__(self, way):
        self.way = way

    def __hash__(self):
        return hash(tuple(self.way.points))

    def __eq__(self, other):
        return (self.way.points == other.way.points)

def getDuplicates(items):
    l.debug("Making list")
    dups = {}
    for i in items:
        if i in dups:
            dups[i].append(i)
        else:
            dups[i] = [i]
    return dups

def getParent(w):
    return iter(w.parents).next()

# We handle two sorts of duplicate Ways here.  One is a set of stand-alone Ways
# with parent Features that have some tags.  The other case is a set of Ways
# that have multipolygon Relation parents and Feature grandparents with tags.
def preOutputTransform(geometries, features):
    ways = [ComparableWay(w) for w in geometries if type(w) == ogr2osm.Way and \
            type(getParent(w)) == ogr2osm.Feature]
    for (way, dups) in getDuplicates(ways).items():
        if len(dups) == 1:
            continue
        l.info("Resolving " + str(len(dups)) + " duplicate ways")
        final = None
        ordered = sorted(ways, key=lambda w: getParent(w.way).tags['apn'])
        final_tags = {}
        index = 0
        for w in ordered:
            p = getParent(w.way)
            final_tags['apn:%d' % (index)] = p.tags['apn']
            if index != 0:
                features.remove(p)
                p.geometry.removeparent(getParent(w.way))
            index += 1

        tags = getParent(ordered[0].way).tags
        del tags['apn']
        tags.update(final_tags)
