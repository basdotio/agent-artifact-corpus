#!/usr/bin/env bash

# Prepares the environment to execute this script.
function prepareToInstall() {
    PYTHON_CMD=$(which python3)

    $PYTHON_CMD -m venv .venv

    source .venv/bin/activate
}

# Installs the required Python packages.
function install() {
    prepareToInstall

    PIP_CMD=$(which pip)

    $PIP_CMD install -r requirements.txt
    $PIP_CMD install --upgrade pip 
}

install
