# django_example
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## Развернуть проект
### 0 Скопировать compose файл для разработки в корень проекта
```bash
cp dockerfiles/docker-compose.dev.yml docker-compose.yml -l
```

### 1 Собрать, прогнать миграции, накатить фикстуры:
```bash
make project_build
make project_reset
```

### 2 Обновить `/etc/hosts`
добавить в `/etc/hosts` запись:
```
127.0.0.1  example.localhost
```

### 3 Зайти в админку
```
http://example.localhost:8000/admin/
```
Логин `admin@django_example.ru`, пароль `123321`.


Useful commands
-------------
#### Rebuild web
```bash
docker-compose kill web && docker-compose rm web && docker rmi django_exapmle_web:latest && docker-compose build web
```

#### autoformat code with [black](https://black.readthedocs.io/en/stable/) 
```bash
docker-compose run web black apps/clinics/admin.py
```

#### flake8 
```bash
docker-compose run web flake8 apps/clinics/admin.py
```

#### Allow ipdb for local dev
```bash
docker-compose run --service-ports web python manage.py runserver 0.0.0.0:8000
```
