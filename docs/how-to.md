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
pipenv run pytest -x
```

## Set up Gitpod environment
1. Make sure there is a branch available in the Github repository
2. Go to the workspace overview in Gitpod of TGWF
3. Run pre-build
    Click on the pre-build option in the workspace overview of the workspace you want to prepare.
4. After this preparation, open the workspace and it's ready to be used
