Server Setup
============

OpenParcelMap relies on a number of components.  I'm mostly documenting this
here for easier administration.  But perhaps these notes are handy.  Before you
proceed, you should understand the OSM [component overview]
(http://wiki.openstreetmap.org/wiki/Component_overview).  BTW, these are all
instructions for Ubuntu.

rails port
==========

The [rails port] (http://wiki.openstreetmap.org/wiki/The_Rails_Port) is the API
server used by OSM.  The first step here is to set up an instance of the rails
port for collecting parcel data.  Here are some notes:

* I deployed the production code to /srv/openparcelmap/openstreetmap-website by
  cloning the forked repository.  I set the permissions so that anyone in the
  www-data group (including me and apache) can read and write.

      sudo mkdir -p /srv/openparcelmap
      sudo chown yourname.yourgroup /srv/openparcelmap/
      cd /srv/openparcelmap
      git clone git@github.com:ual/openstreetmap-website.git
      sudo chown -R www-data:www-data openstreetmap-website/
      sudo chmod -R g+w openstreetmap-website/
      sudo chmod -R g+s openstreetmap-website/

* I used the [Phusion Passenger]
  (http://www.modrails.com/documentation/Users%20guide%20Apache.html#_deploying_a_rack_based_ruby_application_including_rails_gt_3)
  to run the application under apache.

* I edited the configuration in config/application.yml so that the application
  could send email.  Note that for this to work I had to "apt-get install
  sendmail-base sendmail"

osmosis
=======

Osmosis feeds the Internet with planet dumps.  The main reference for osmosis
is: http://wiki.openstreetmap.org/wiki/Osmosis/Detailed_Usage.  We are using
osmosis like planet.openstreetmap.org as described here:
http://wiki.openstreetmap.org/wiki/Osmosis/Replication

1. Make an osmosis user and create all of the directories that she needs.

    sudo adduser --system osmosis
    sudo mkdir /var/www/planet
    sudo chown osmosis.nogroup /var/www/planet
    sudo passwd osmosis
    sudo usermod -s /bin/bash -a -G sys osmosis

2. Login as the osmosis user and set a few things up:

    su osmosis 
    echo 'export PATH=~/bin:$PATH' >> ~/.bashrc
    echo 'JAVACMD_OPTIONS="-Xmx16G -server"' > ~/.osmosis
    source ~/.bashrc
    mkdir -p ~/bin ~/app/osmosis

3. Fetch, install, and setup the latest osmosis:

    cd ~/app/osmosis
    wget http://bretth.dev.openstreetmap.org/osmosis-build/osmosis-latest.tgz
    tar -xzf osmosis-latest.tgz
    ln -s ~/app/osmosis/bin/osmosis ~/bin/osmosis
    ln -s /var/www/planet ~/planet
    mkdir -p ~/app/replicate/data
    mkdir -p ~/app/replicate-hour/data
    mkdir -p ~/app/replicate-day/data

4. Create an auth file for osmosis to user to access the rails port DB.  I do
   this in ~/opm.auth.  The contents should look like this.

    host=localhost
    database=openparcelmap
    user=openparcelmap
    password=yourpassword
    dbType=postgresql

   I recommend restricting read access to this file since it contains a password:

    chmod 600 opm.auth

5. Create the first planet dump

    osmosis --read-apidb authFile=~/opm.auth validateSchemaVersion=no \
    --write-xml /var/www/planet/planet-latest.bz2

6. Go learn more about replication and planet file management and make osmosis
   run under cron and generate replication diffs.

tile rendering database
=======================

Tiles are rendered from a postgis database that is regularly sync'd with the
planet dumps.

1. Create a suitable user and DB

    createuser -S -D -R -P opm
    createdb -O opm opmtile_dev
    createdb -T template_postgis opmtile_dev

2. Get [the latest planet file]
   (http://opm.ual.berkeley.edu/planet/planet-latest.osm.bz2.)

3. Import planet file:

    echo 'node,way   BLKLOT      text         polygon' > foo.style
    osm2pgsql -s -S foo.style -d opmtile_dev -U opm -H localhost -W planet-latest.osm.bz2

tile renderer
=============

We use mod_tile and mapnik to render tiles.
