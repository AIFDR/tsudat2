#!/bin/bash

#
# A script to recreate the fake_ui_files.VictorHarbour data directory
# We don't put this directory into git as it's big!
#
# A better approach might be to keep a zipped copy of the data on alamba
# and scp that single file to here and unzip.
#

# put your name here - you'll need to enter your password below
USERNAME=wilsor

# where to create fake_ui data
TARGET=fake_ui_files.VictorHarbour

# source base on alamba
SOURCE=/model_area/inundation/data/south_australia/victor_harbor_tsunami_scenario_2010/anuga

# source of patched/new files
PATCHDIR=fake_ui_files.VH

# don't run if target dir exists
if [ -d $TARGET ]; then
    echo "Sorry, directory $TARGET exists.  Delete it first."
    exit
fi

mkdir -p $TARGET
mkdir -p $TARGET/boundaries
mkdir -p $TARGET/gauges
mkdir -p $TARGET/polygons
mkdir -p $TARGET/raw_elevations

# copy required files from alamba
scp $USERNAME@alamba:$SOURCE/boundaries/landward_boundary.csv $TARGET/boundaries
scp $USERNAME@alamba:$SOURCE/boundaries/urs_order.csv $TARGET/boundaries
scp $USERNAME@alamba:$SOURCE/boundaries/58342/victor_harbor.sts $TARGET/boundaries/VictorHarbour.sts
scp $USERNAME@alamba:$SOURCE/gauges/gauges_final.csv $TARGET/gauges
scp $USERNAME@alamba:$SOURCE/polygons/area_of_interest.csv $TARGET/polygons
scp $USERNAME@alamba:$SOURCE/polygons/area_of_significance.csv $TARGET/polygons
scp $USERNAME@alamba:$SOURCE/polygons/bounding_polygon.csv $TARGET/polygons
scp $USERNAME@alamba:$SOURCE/polygons/shallow_water.csv $TARGET/polygons
scp $USERNAME@alamba:$SOURCE/topographies/250m_final.csv $TARGET/raw_elevations
scp $USERNAME@alamba:$SOURCE/topographies/aoi.csv $TARGET/raw_elevations
scp $USERNAME@alamba:$SOURCE/topographies/shallow_water.csv $TARGET/raw_elevations

# patch original data with changed files here
cp $PATCHDIR/interior_hp.csv $TARGET/boundaries
