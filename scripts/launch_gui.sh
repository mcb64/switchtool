#!/bin/bash

#export PCDS_CONDA_VER=5.4.1
#source /cds/group/pcds/pyps/conda/pcds_conda
source ~mcbrowne/.conda/envs/mcb-test/etc/profile.d/conda.sh
conda activate mcb-test

# Find full path of release directory.
export RELDIR=`readlink -f $0`
export RELDIR=`dirname $RELDIR`
export RELDIR=`dirname $RELDIR`
export PYTHONPATH=$RELDIR

python $RELDIR/scripts/switch_gui.py "$@"
