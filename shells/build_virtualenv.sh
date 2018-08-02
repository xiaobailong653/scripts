#!/usr/bin/env bash
#

echo "Install virtualenv and virtualenvwrapper"
pip install virtualenv
pip install virtualenvwrapper

mkdir -p $HOME/.virtualenvs $HOME/workspace

cat >> $HOME/.bashrc <<EOF

# workon
export WORKON_HOME=$HOME/.virtualenvs
export PROJECT_HOME=$HOME/workspace
source /usr/local/bin/virtualenvwrapper.sh
EOF
source $HOME/.bashrc