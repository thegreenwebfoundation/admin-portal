# How to...

## Debug issues on production and staging
All application errors are sent to Sentry: https://sentry.io/organizations/product-science/projects/.

The details of Django errors from the web portal are accessible in the [`admin-portal` Sentry project](https://sentry.io/organizations/product-science/projects/admin-portal/?project=2071451). You can filter by environment to access errors either from production or staging.

## Run tests using pytest

pytest.ini is called before running a pytest.
This file specifies what django settings (ds) to use, which annotated to exclude using the mark (-m) keyword and other functions.

#### Run all tests
Important: make sure to be outside of an enviroment (deactivate).
```
./run-tests.sh
```

#### Run all test until one fails
```
dotenv run -- pytest -x
```

## Set up Gitpod environment
1. Make sure there is a branch available in the Github repository
2. Go to the workspace overview in Gitpod of TGWF
3. Run pre-build
    Click on the pre-build option in the workspace overview of the workspace you want to prepare.
4. After this preparation, open the workspace and it's ready to be used


### Fetch files from object storage

We try to treat our deployed applications as ephemeral, and store any meaningful state in a database or in object storage.

Instead of using Amazon Web Services, we used Scaleway's AWS S3 compatible object storage service. See our the object_storage.py for a convenience methods when working with object storage in a provider agnostic fashion.

This project also uses libraries to allow the use the handy `aws` cli tool with Scaleway object storage, to make it relatively easy to syn directories with `sync`, upload and download files with `cp` and so on.


*Examples*

_(These all assume you are running `dotenv run -- $COMMAND` to load the necessary environment variables into your shell)_:

See the buckets you have access to:

```
aws s3 ls
```

See all the files in beneath a given path, with the sizes in a human readable fashion, listing the total size as a summary (careful on large buckets!)

```
aws s3 ls s3://your-bucket/ --human-readable --summarize --recursive
```

Upload a file to object storage

```
aws s3 cp local.file.zip s3://destination-bucket/path/to/remote.file.zip
```

Download a file from object storage

```
aws s3 cp s3://your-bucket/path/to/remote.file.zip local.file.zip
```

Move all the files at one path in one a bucket to a path in a different one

```
aws s3 sync  s3://origin-bucket/path/to/migrate s3://destination-bucket/new/destination/path/
```
