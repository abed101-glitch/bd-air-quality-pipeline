VENV := .venv
PY := $(VENV)/bin/python
DBT := cd dbt && ../$(VENV)/bin/dbt
export PYTHONPATH := src

.PHONY: setup backfill incremental dbt test report dashboard airflow-setup airflow lint

setup:            ## create the project virtualenv
	uv venv --python 3.12 $(VENV) && uv pip install --python $(PY) -r requirements.txt

backfill:         ## load 2024-01-01 .. yesterday
	$(PY) -m bdair.pipeline backfill

incremental:      ## load new data since the last run (7-day lookback)
	$(PY) -m bdair.pipeline incremental

dbt:              ## seeds, models and data tests
	$(DBT) build --profiles-dir .

test:             ## unit tests
	$(PY) -m pytest -q

lint:
	$(VENV)/bin/ruff check src tests dags analysis dashboard

report:           ## charts + findings.json into docs/
	$(PY) analysis/make_report.py

dashboard:
	$(VENV)/bin/streamlit run dashboard/app.py

airflow-setup:    ## separate virtualenv for Airflow
	uv venv --python 3.12 .venv-airflow && uv pip install --python .venv-airflow/bin/python -r requirements-airflow.txt

airflow:          ## local Airflow (UI on :8080) with this repo's dags/ folder
	AIRFLOW_HOME=$(CURDIR)/.airflow AIRFLOW__CORE__DAGS_FOLDER=$(CURDIR)/dags \
	AIRFLOW__CORE__LOAD_EXAMPLES=False BDAIR_HOME=$(CURDIR) .venv-airflow/bin/airflow standalone
