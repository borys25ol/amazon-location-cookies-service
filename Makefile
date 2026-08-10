# uv reads .python-version, so everyone gets the interpreter the image ships.
ve:
	@command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
	uv venv --seed .ve
	uv pip install --python .ve/bin/python -r requirements.txt
	.ve/bin/playwright install chromium

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

runscrapyrt:
	scrapyrt --ip 0.0.0.0 --port 7800

runserver:
	uvicorn main.api.app:app --host 0.0.0.0 --port 8000 --reload

install_hooks:
	uv pip install --python .ve/bin/python -r requirements-ci.txt
	.ve/bin/pre-commit install

run_hooks:
	pre-commit run --all-files

test:
	pytest tests

style:
	flake8 main tests && isort main tests --diff && black main tests --check

types:
	mypy --namespace-packages -p "main" --config-file setup.cfg
