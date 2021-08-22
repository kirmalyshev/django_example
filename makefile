$(eval SHA=$(shell sh -c "git rev-parse HEAD|head -c 6"))
IMAGE = django_example

# create base image: linux package & python package
# manually build on modified pip file
build_base:
	docker-compose build --no-cache base

build_web:
	docker-compose build web

build_web_no_cache:
	docker-compose build --no-cache web

project_build:
	make build_web

project_reset:
	docker-compose kill web
	docker-compose up -d db
	docker-compose run web python manage.py reset_db
	make migrate
# rm redundant containers
	docker-compose rm --stop --force web
	docker-compose up -d web
	docker-compose exec web python manage.py collectstatic --no-input --clear

restart:
	docker-compose kill web
	docker-compose rm --stop --force web
	docker-compose up -d
	make -i restart_celery_daemons

# for VDS staging, without nginx
pull_restart:
	git pull
	make clean_pyc
	make build_web
	make migrate
	make restart

pull_rebuild_restart:
	git pull
	make project_build
	make migrate
	make restart

restart_celery_daemons:
	chmod +x server_tools/reload_celery.sh && ./server_tools/reload_celery.sh

# Dev
up:
	docker-compose up web

test:
	docker-compose run web python manage.py test --keepdb

mypy:
	docker-compose run web mypy django_example/ apps/

clean_pyc:
	find . -type f -iname "*.pyc" -delete

black:
	docker-compose run web black apps/appointments

shell_plus:
	docker-compose run web python manage.py shell_plus

migrate:
	docker-compose run web python manage.py migrate
