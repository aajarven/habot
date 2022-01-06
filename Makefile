lint: pylint flake

pylint:
	pylint habot tests --disable=fixme,duplicate-code

flake:
	flake8 habot tests
