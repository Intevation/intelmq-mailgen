all:
	@echo "No default target defined.  Available: 'check'."

check:
	cd tests && python3 -m unittest

PHONY: all check
