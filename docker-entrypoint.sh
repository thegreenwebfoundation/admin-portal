#!/bin/bash
set -e

#######
# Killer function
die() {
    printf '%s\n' "$1" >&2
    exit 1
}
#######
# Argument loop
while (( $# )); do
    case $1 in
        migrate)
            python manage.py migrate || exit $?
            ;;
        collectstatic)
            python manage.py collectstatic --noinput || exit $?
            ;;
        coverage)
            coverage run --source='.' manage.py test && coverage report || exit $?
            ;;
        run_dev)
            python manage.py runserver 0:8000 || exit $?
            ;;
        run)
            gunicorn -c gunicorn_config.ini media_observation_database.wsgi || exit $?
            ;;
        pass)
            if [ "$2" ]; then
                python manage.py "$2" || exit $?
                shift
            else
                die 'ERROR: "pass" requires a non-empty option argument.'
            fi
            ;;
        *)
            break
    esac

    shift
done

exec "$@"
