#!/bin/bash

#
# A script to recreate the fake_ui_files.BatemansBay data directory
# We don't put this directory into git as it's big!
#
# A better approach might be to keep a zipped copy of the data on alamba
# and scp that single file to here and unzip.
#

# put your name here - you'll need to enter your password below
USERNAME=graydu

# where to create fake_ui data
TARGET=fake_ui_files.BatemansBay

# source base on alamba
SOURCE=/model_area/inundation/data/new_south_wales/batemans_bay_tsunami_scenario_2009/anuga

# source of patched/new files
PATCHDIR=fake_ui_files.BB

# don't run if target dir exists
#if [ -d $TARGET ]; then
#    echo "Sorry, directory $TARGET exists.  Delete it first."
#    exit
#fi

mkdir -p $TARGET
mkdir -p $TARGET/boundaries
mkdir -p $TARGET/gauges
mkdir -p $TARGET/polygons
mkdir -p $TARGET/topographies
mkdir -p $TARGET/raw_elevations

# copy required files from alamba
rsync $USERNAME@alamba.aifdr.org:$SOURCE/boundaries/landward_boundary.csv $TARGET/boundaries
rsync $USERNAME@alamba.aifdr.org:$SOURCE/boundaries/urs_order.csv $TARGET/boundaries
rsync $USERNAME@alamba.aifdr.org:$SOURCE/boundaries/58348/batemans_bay.sts $TARGET/boundaries/BatemansBay.sts
rsync $USERNAME@alamba.aifdr.org:$SOURCE/gauges/gauges.csv $TARGET/gauges
rsync $USERNAME@alamba.aifdr.org:$SOURCE/polygons/area_of_interest.csv $TARGET/polygons
rsync $USERNAME@alamba.aifdr.org:$SOURCE/polygons/area_of_significance.csv $TARGET/polygons
rsync $USERNAME@alamba.aifdr.org:$SOURCE/polygons/bounding_polygon.csv $TARGET/polygons
rsync $USERNAME@alamba.aifdr.org:$SOURCE/polygons/shallow_water.csv $TARGET/polygons
rsync $USERNAME@alamba.aifdr.org:$SOURCE/topographies/batemans_bay_combined_elevation.pts $TARGET/topographies/combined_elevation.pts

# patch original data with changed files here
cp $PATCHDIR/interior_hp.csv $TARGET/boundaries
