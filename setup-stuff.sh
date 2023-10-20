cp ./.env.gitpod ./.env
mysqladmin create greencheck
python -m pipenv install --dev
python -m pipenv run python ./manage.py migrate
python -m pipenv run python ./manage.py tailwind install
python -m pipenv run python ./manage.py tailwind build
cd ./apps/theme/static_src/
npx rollup --config
cd ../../../
python -m pipenv run python ./manage.py collectstatic --no-input