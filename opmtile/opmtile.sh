#!/bin/bash

MYDIR=`dirname ${0}`
OPMTILE=/srv/openparcelmap/opmtile
STYLE=${MYDIR}/opmtile-osm2pgsql.style
DB=opmtile_dev
DBUSER=opm

function log() {
	logger "opmtile: $*"
}

function cmd_or_fail() {
	CMD=$*
	MSG=`${CMD}`
	if [ $? -ne 0 ]; then
		log "FAILED: ${CMD}"
		log ${MSG}
		log "state.txt:"
		log `cat ${OPMTILE}/state.txt`
        log "reverting state.txt"
        cp ${OPMTILE}/state.txt.backup ${OPMTILE}/state.txt
		exit 1
	fi
}

cp ${OPMTILE}/state.txt ${OPMTILE}/state.txt.backup
cmd_or_fail osmosis --read-replication-interval workingDirectory=${OPMTILE} --simplify-change --write-xml-change changes.osc.gz
cmd_or_fail osm2pgsql --append -s -S ${STYLE} -d ${DB} -U ${DBUSER} -H localhost changes.osc.gz
