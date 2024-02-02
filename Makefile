# Makefile

# Target for running in detached mode
build:
	docker-compose -f local.yml build
up:
	docker-compose -f local.yml up -d

down:
	docker-compose -f local.yml down

make_migrations:
	docker-compose -f local.yml run --rm django python manage.py makemigrations

migrate:
	docker-compose -f local.yml run --rm django python manage.py migrate

test:
	docker-compose -f local.yml run --rm django coverage run -m pytest
