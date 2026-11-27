#!/usr/bin/env bash
# Piloto 14.2: monolitico (BC 0-99) e shards A (0-49), B (50-99), em paralelo.
source ~/miniforge3/bin/activate ambiente_fisica
set -u
cd <repo>
B=./build/pythia_geant
/usr/bin/time -v $B --config config/production.conf --events 100 --output <repo>/outputs/cycle14-2-pilot/monolithic.root > <repo>/outputs/cycle14-2-pilot/logs/monolithic.log 2> <repo>/outputs/cycle14-2-pilot/logs/monolithic.time &
/usr/bin/time -v $B --config config/production.conf --events 50 --output <repo>/outputs/cycle14-2-pilot/shard-a.root > <repo>/outputs/cycle14-2-pilot/logs/shard-a.log 2> <repo>/outputs/cycle14-2-pilot/logs/shard-a.time &
/usr/bin/time -v $B --config <repo>/outputs/cycle14-2-pilot/config/shard-b.conf > <repo>/outputs/cycle14-2-pilot/logs/shard-b.log 2> <repo>/outputs/cycle14-2-pilot/logs/shard-b.time &
wait
echo PILOT_DONE
