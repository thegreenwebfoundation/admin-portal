#!/bin/bash

# this is convenience script when iterating on container builds
# most of the time we would use the makefile docker.build, but 
# this is intended for debugging, and logging into containers 
# when inspecting their contents

set -euo pipefail

# create our container
docker build . --tag greenweb-app

# uncommment to log into our newly created container
# docker run  --env-file .env.docker  --interactive --tty greenweb-app bash
