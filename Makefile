.PHONY: install load ratios test report dashboard api clean

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

load:
	python src/etl/loader.py

test:
	pytest tests/ -v --tb=short --html=reports/pytest_report.html --self-contained-html

ratios:
	@echo "Sprint 2 target (Days 8-14) — financial ratio engine not yet implemented."

report:
	@echo "Sprint 5 target (Days 29-35) — PDF tearsheets/sector reports not yet implemented."

dashboard:
	@echo "Sprint 4 target (Days 22-28) — Streamlit app not yet implemented. Will run on localhost:8501."
	# streamlit run src/dashboard/app.py

api:
	@echo "Sprint 6 target (Days 36-45) — FastAPI server not yet implemented."
	# uvicorn src.api.main:app --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -f db/nifty100.db
