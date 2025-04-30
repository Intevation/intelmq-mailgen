check:
	pytest tests/

check_all:
	ALLTESTS=1 pytest tests/ -v

.PHONY: check docs

docs:
	make -C docs html

pycodestyle:
	pycodestyle docs/ example_scripts/ extras/ intelmqmail/ sql/ templates/ tests/
