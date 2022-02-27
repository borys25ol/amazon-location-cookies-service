ve:
	python3 -m venv .ve; \
	. .ve/bin/activate; \
	pip install -r requirements.txt; \

clean:
	test -d .ve && rm -rf .ve

docker_build:
	docker-compose up -d --build

docker_up:
	docker-compose up -d

docker_start:
	docker-compose start

docker_down:
	docker-compose down

docker_destroy:
	docker-compose down -v

docker_stop:
	docker-compose stop

docker_restart:
	docker-compose stop
	docker-compose up -d

docker_logs:
	docker-compose logs --tail=100 -f

register_user:
	export PYTHONPATH=. && export APP_ENV=prod && python ./main/cli.py register-user

register_test_user:
	export PYTHONPATH=. && export APP_ENV=test && python ./main/cli.py register-user

add_test_config:
	export PYTHONPATH=. && export APP_ENV=test && python ./main/cli.py add-test-project-config

runserver-prod:
	uvicorn main.app:app --host 0.0.0.0 --port 5000 --reload

runserver-dev:
	 export APP_ENV=dev && uvicorn main.app:app --host 0.0.0.0 --port 5000 --reload

runserver-test:
	 export APP_ENV=test && uvicorn main.app:app --host 0.0.0.0 --port 5000 --reload

test:
	export APP_ENV=test && python -m pytest -v ./tests

test-cov:
	export APP_ENV=test && python -m pytest  --cov=./main ./tests

install_hooks:
	pip install -r requirements-ci.txt; \
	pre-commit install; \

run_hooks_on_all_files:
	pre-commit run --all-files

style:
	flake8 main && isort main --diff && black main --check

types:
	mypy --namespace-packages -p "main" --config-file setup.cfg
