#!/bin/bash

# This script entirely resets the current database (given in DATABASE_URL)
# and object storage bucket (given in OBJECT_STORAGE_BUCKET_NAME)
# from another environment, given as a mysql dump file with CLONE_FROM_DB_DUMP
# and the name of a source bucket, given in CLONE_FROM_OBJECT_STORAGE_BUCKET.

set -eo pipefail

if [[ -z $CLONE_FROM_DB_DUMP || -z $CLONE_FROM_OBJECT_STORAGE_BUCKET ]]; then
    cat << EndOfMessage
clone_db.sh requires the following environment variables to be set:
   - CLONE_FROM_DB_DUMP: The path to the db dump file to import
   - CLONE_FROM_OBJECT_STORAGE_BUCKET: The name of the object storage bucket to import assets from.
In addition, it assumes the following environment variables, taken from your .env file:
   - DATABASE_URL: The connection url for the database you want to import TO
   - OBJECT_STORAGE_BUCKET_NAME: The name of the object storage bucket to clone assets TO

It also requires mcli to be correctly configured to access both buckets, with the prefix "s3/"
EndOfMessage
    exit 2;
fi

DATABASE_USER=$(echo $DATABASE_URL | grep -oP "mysql://\K(.+?):" | cut -d: -f1)
DATABASE_PASSWORD=$(echo $DATABASE_URL | grep -oP "mysql://.*:\K(.+?)@" | cut -d@ -f1)
DATABASE_HOST=$(echo $DATABASE_URL | grep -oP "mysql://.*@\K(.+?):" | cut -d: -f1)
DATABASE_PORT=$(echo $DATABASE_URL | grep -oP "mysql://.*@.*:\K(\d+)/" | cut -d/ -f1)
DATABASE_NAME=$(echo $DATABASE_URL | grep -oP "mysql://.*@.*:.*/\K(.+?)$")

cat << EndOfMessage
WARNING! clone_db.sh is a DESTRUCTIVE operation!
If you continue, the following will happen:
- Your database at ${DATABASE_URL} will be cleared.
- The database dump at ${CLONE_FROM_DB_DUMP} will be imported into ${DATABASE_URL}
- All the files in the object storage bucket "${CLONE_FROM_OBJECT_STORAGE_BUCKET}" will be cloned into "${OBJECT_STORAGE_BUCKET_NAME}", overwriting any existing files with the same key.
Are you sure you want to continue?
EndOfMessage

read -p "Confirm TARGET database host ($DATABASE_HOST): " confirm_host
read -p "Confirm TARGET database name ($DATABASE_NAME): " confirm_database
read -p "Confirm TARGET object storage bucket name ($OBJECT_STORAGE_BUCKET_NAME): " confirm_bucket_name
read -n 1 -p "Start the clone operation? (y/N): " confirm

if [ "$confirm_host" = "$DATABASE_HOST" ] && [ "$confirm_database" = "$DATABASE_NAME" ] && [ "$confirm_bucket_name" = "$OBJECT_STORAGE_BUCKET_NAME" ] && [ "$confirm" = "y" ]; then
    printf "\nCloning database...\n"
    mysql -u $DATABASE_USER -p$DATABASE_PASSWORD -h $DATABASE_HOST -P $DATABASE_PORT $DATABASE_NAME < $CLONE_FROM_DB_DUMP
    printf "Cloning S3 bucket...\n"
    mcli mirror s3/$CLONE_FROM_OBJECT_STORAGE_BUCKET s3/$OBJECT_STORAGE_BUCKET_NAME --overwrite
    printf "Done!\n"
else
    printf "\nAborting!\n"
    exit 1;
fi
