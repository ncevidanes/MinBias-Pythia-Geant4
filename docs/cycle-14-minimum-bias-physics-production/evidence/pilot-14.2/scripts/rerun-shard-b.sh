#!/usr/bin/env bash
source ~/miniforge3/bin/activate ambiente_fisica
set -u
cd <repo>
/usr/bin/time -v ./build/pythia_geant --config <repo>/outputs/cycle14-2-pilot/config/shard-b.conf > <repo>/outputs/cycle14-2-pilot/logs/shard-b.log 2> <repo>/outputs/cycle14-2-pilot/logs/shard-b.time
