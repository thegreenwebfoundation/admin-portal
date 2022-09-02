# How to use..
## Sphinx

## Tests using pytest

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

## Gitpod environment set up steps
1. Make sure there is a branch available in the Github repository
2. Go to the workspace overview in Gitpod of TGWF
3. Run pre-build
    Click on the pre-build option in the workspace overview of the workspace you want to prepare.
4. After this preperation, open the workspace and it's ready to be used