#!/usr/bin/env bash
sh -c "$(cat .release/cmd.txt)" && rm -rf .release
