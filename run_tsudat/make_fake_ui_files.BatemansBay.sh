#!/bin/bash

#
# A script to recreate the fake_ui_files.BatemansBay data directory
# We don't put this directory into git as it's big!
#
# A better approach might be to keep a zipped copy of the data on alamba
# and scp that single file to here and unzip.
#

PW=VBi1bu335

# where to create fake_ui data
TARGET=fake_ui_files.BatemansBay

# source base on alamba
SOURCE=/model_area/inundation/data/new_south_wales/batemans_bay_tsunami_scenario_2009/anuga

# don't run if target dir exists
if [ -d $TARGET ]; then
    echo "Sorry, directory $TARGET exists.  Delete it first."
    exit
fi

echo "password: $PW"

mkdir -p $TARGET
mkdir -p $TARGET/boundaries
mkdir -p $TARGET/gauges
mkdir -p $TARGET/polygons
mkdir -p $TARGET/topographies
mkdir -p $TARGET/raw_elevations

# copy required files from alamba
scp wilsor@alamba:$SOURCE/boundaries/landward_boundary.csv $TARGET/boundaries
scp wilsor@alamba:$SOURCE/boundaries/urs_order.csv $TARGET/boundaries
scp wilsor@alamba:$SOURCE/boundaries/58348/batemans_bay.sts $TARGET/boundaries/BatemansBay.sts
scp wilsor@alamba:$SOURCE/gauges/gauges.csv $TARGET/gauges
scp wilsor@alamba:$SOURCE/polygons/area_of_interest.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/polygons/area_of_significance.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/polygons/bounding_polygon.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/polygons/shallow_water.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/topographies/batemans_bay_combined_elevation.pts $TARGET/topographies/combined_elevation.pts

