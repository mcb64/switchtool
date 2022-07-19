#!/bin/bash

#export PCDS_CONDA_VER=...
#source /cds/group/pcds/pyps/conda/pcds_conda
source /cds/group/pcds/pyps/conda/dev_conda

# Find full path of release directory.  This script is in
# $RELDIR/scripts/launch_gui.sh, so we need to chop off the
# last two path components.
export RELDIR=`readlink -f $0`
export RELDIR=`dirname $RELDIR`
export RELDIR=`dirname $RELDIR`
export PYTHONPATH=$RELDIR

python $RELDIR/scripts/switch_gui.py "$@"
