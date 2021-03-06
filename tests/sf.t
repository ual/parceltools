overlapways:
  $ ogr2osm.py -f $TESTDIR/overlapways.shp -t sf
  running with lxml.etree
  Preparing to convert file .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Successfully loaded 'sf' translation method .* (re)
  Using default filterLayer
  Using default filterFeature
  Using user filterTags
  Using default filterFeaturePost
  Using user preOutputTransform
  Parsing data
  Detected projection metadata:
  PROJCS["Lambert_Conformal_Conic",
      GEOGCS["GCS_North_American_1983",
          DATUM["North_American_Datum_1983",
              SPHEROID["GRS_1980",6378137,298.257222101]],
          PRIMEM["Greenwich",0],
          UNIT["Degree",0.017453292519943295]],
      PROJECTION["Lambert_Conformal_Conic_2SP"],
      PARAMETER["standard_parallel_1",37.06666666666667],
      PARAMETER["standard_parallel_2",38.43333333333333],
      PARAMETER["latitude_of_origin",36.5],
      PARAMETER["central_meridian",-120.5],
      PARAMETER["false_easting",6561666.666666667],
      PARAMETER["false_northing",1640416.666666667],
      UNIT["Foot_US",0.30480060960121924],
      PARAMETER["scale_factor",1.0]]
  Merging points
  Making list
  Checking list
  Resolving 5 duplicate ways
  Outputting XML
  $ xmllint --format overlapways.osm | diff -uNr - $TESTDIR/overlapways-ref.osm

multiparcel:
  $ ogr2osm.py -f $TESTDIR/multiparcel.shp -t sf
  running with lxml.etree
  Preparing to convert file .* (re)
  Will try to detect projection from source metadata, or fall back to EPSG:4326
  Successfully loaded 'sf' translation method .* (re)
  Using default filterLayer
  Using default filterFeature
  Using user filterTags
  Using default filterFeaturePost
  Using user preOutputTransform
  Parsing data
  Detected projection metadata:
  PROJCS["NAD_1983_StatePlane_California_III_FIPS_0403_Feet",
      GEOGCS["GCS_North_American_1983",
          DATUM["North_American_Datum_1983",
              SPHEROID["GRS_1980",6378137.0,298.257222101]],
          PRIMEM["Greenwich",0.0],
          UNIT["Degree",0.017453292519943295]],
      PROJECTION["Lambert_Conformal_Conic_2SP"],
      PARAMETER["False_Easting",6561666.666666666],
      PARAMETER["False_Northing",1640416.666666667],
      PARAMETER["Central_Meridian",-120.5],
      PARAMETER["Standard_Parallel_1",37.06666666666667],
      PARAMETER["Standard_Parallel_2",38.43333333333333],
      PARAMETER["Latitude_Of_Origin",36.5],
      UNIT["Foot_US",0.30480060960121924],
      PARAMETER["scale_factor",1.0]]
  Merging points
  Making list
  Checking list
  Resolving 4 duplicate ways
  Resolving 4 duplicate ways
  Resolving 4 duplicate relations
  Outputting XML
  $ xmllint --format multiparcel.osm | diff -uNr - $TESTDIR/multiparcel-ref.osm
