all:
	@/bin/echo -n "No default target defined."
	@/bin/echo " Available: check, check_all"

check:
	python3 -m unittest discover --start-directory tests -v

check_all:
	ALLTESTS=1 python3 -m unittest discover --start-directory tests -v

.PHONY: all check check_all docs

sync:
	rsync -a * .github --exclude '*.pyc' --exclude __pycache__ --exclude dist --exclude intelmqmail.egg-info docker-swa.whale.intevation.de:intelmq-mailgen/

docs:
	make -C docs html

pycodestyle:
	pycodestyle docs/ example_scripts/ extras/ intelmqmail/ sql/ templates/ tests/
