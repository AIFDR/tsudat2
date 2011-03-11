#!/bin/bash

#
# A script to recreate the fake_ui_files.VictorHarbour data directory
#

PW=VBi1bu335

# where to create fake_ui data
TARGET=fake_ui_files.VictorHarbour

# source base on alamba
SOURCE=/model_area/inundation/data/south_australia/victor_harbor_tsunami_scenario_2010/anuga

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
mkdir -p $TARGET/raw_elevations

# copy required files from alamba
scp wilsor@alamba:$SOURCE/boundaries/landward_boundary.csv $TARGET/boundaries
scp wilsor@alamba:$SOURCE/boundaries/urs_order.csv $TARGET/boundaries
scp wilsor@alamba:$SOURCE/boundaries/58342/victor_harbor.sts $TARGET/boundaries/VictorHarbour.sts
scp wilsor@alamba:$SOURCE/gauges/gauges_final.csv $TARGET/gauges
scp wilsor@alamba:$SOURCE/polygons/area_of_interest.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/polygons/area_of_significance.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/polygons/bounding_polygon.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/polygons/shallow_water.csv $TARGET/polygons
scp wilsor@alamba:$SOURCE/topographies/250m_final.csv $TARGET/raw_elevations
scp wilsor@alamba:$SOURCE/topographies/aoi.csv $TARGET/raw_elevations
scp wilsor@alamba:$SOURCE/topographies/shallow_water.csv $TARGET/raw_elevations

