#!/bin/bash

cd ~/MonteMarkets

python -m backend.worker &
python -m backend.worker &
python -m backend.worker &
python -m backend.worker &

wait
