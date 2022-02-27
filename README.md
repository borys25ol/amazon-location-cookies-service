Scraping Module API
====================

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://github.com/tiangolo/fastapi)

![Deploy prod workflow](https://github.com/Simporter/scraping-module-api/actions/workflows/deploy_prod.yml/badge.svg)
![Run linters](https://github.com/Simporter/scraping-module-api/actions/workflows/run_linters.yml/badge.svg)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Pre-commit: enabled](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=flat)](https://github.com/pre-commit/pre-commit)
[![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg?style=flat)](https://github.com/nedbat/coveragepy)

Developing
-----------

Install pre-commit hooks to ensure code quality checks and style checks


    $ make install_hooks

Then see `Configuration` section

You can also use these commands during dev process:

- to run mypy checks


      $ make types

Configuration
--------------

Replace `.env.example` with real `.env`, changing placeholders

```
SECRET_KEY=changeme

MONGO_DB=<mongo-database>
MONGO_HOST=<mongo-host>
MONGO_PORT=<mongo-host>
MONGO_USER=<mongo-username>
MONGO_PASSWORD=<mongo-password>
MONGO_AUTH_SOURCE=<mongo-auth-source>
MONGO_TASKS_COLLECTION=<mongo-collection>
MONGO_USERS_COLLECTION=<mongo-collection>

ELASTIC_HOST=<elastic-host>
ELASTIC_PORT=<elastic-port>

SCRAPYD_API_URL=<scrapyd-api-url>
SCRAPYD_API_NODE=<scrapyd-api-node>

RUN_BACKGROUND_TASKS=<1|0>
SCHEDULER_TASK_INTERVAL=<seconds-interval>

MAX_CONCURRENT_SUBTASKS=<max-parallel-tasks>

GRAYLOG_HOST=<graylog-host>
GRAYLOG_INPUT_PORT=<graylog-port>

SENTRY_DSN=<sentry-dsn>

GOOGLE_CLOUD_CREDENTIALS=<path-to-json-file>
GOOGLE_CLOUD_PROJECT_ID=<google-project-id>
GOOGLE_CLOUD_BUCKET=<google-bucket>
```

Local install
-------------

Setup and activate a python3 virtualenv via your preferred method. e.g. and install production requirements:


    $ make ve

For remove virtualenv:


    $ make clean


Local run
-------------
Export path to Environment Variables:


    $ export PYTHONPATH='.'

Run server with test settings:


    $ make runserver-test

Run server with dev settings:


    $ make runserver-dev

Run server with prod settings:


    $ make runserver-prod

If everything is fine, check this endpoint:


    $ curl -X "GET" http://host:port/api/v1/status

Expected result:

```
{
  "success": true,
  "version": "<version>",
  "message": "Scraping Module API"
}
```
