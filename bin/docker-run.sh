#!/bin/sh
docker run --rm -it \
       -p 8000:8000 \
       --env-file .env \
       -v $GOOGLE_APPLICATION_CREDENTIALS:/app/service-account.json \
       -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
       $GAR_IMAGE:dev
