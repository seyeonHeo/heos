all:
	@echo 'OMAS makefile help'
	@echo ''
	@echo ' - make tests         : run all regression tests'
	@echo ' - make omfit_tests   : run test_omas in OMFIT'
	@echo ' - make requirements  : build requirements.txt'
	@echo ' - make json          : generate IMAS json structure files'
	@echo ' - make docs          : generate sphinx documentation and pushes it online'
	@echo ' - make tag           : tag git repository with omas/version and push'
	@echo ' - make cocos         : generate list of COCOS transformations'
	@echo ' - make release       : all of the above, in order'
	@echo ' - make pypi          : upload to pypi'
	@echo ' - make html          : generate sphinx documentation'
	@echo ' - make examples      : generate sphinx documentation with examples'
	@echo ' - make site-packages : pip install requirements in site-packages folder'
	@echo ''

TEST_FLAGS=-s omas/tests -v -f

tests:
	python3 -m unittest discover --pattern="*.py" ${TEST_FLAGS}

tests_core:
	python3 -m unittest discover --pattern="*_core.py" ${TEST_FLAGS}

tests_plot:
	python3 -m unittest discover --pattern="*_plot.py" ${TEST_FLAGS}

tests_physics:
	python3 -m unittest discover --pattern="*_physics.py" ${TEST_FLAGS}

tests_utils:
	python3 -m unittest discover --pattern="*_utils.py" ${TEST_FLAGS}

tests_examples:
	python3 -m unittest discover --pattern="*_examples.py" ${TEST_FLAGS}

tests_suite:
	python3 -m unittest discover --pattern="*_suite.py" ${TEST_FLAGS}

tests_examples:
	python3 -m unittest discover --pattern="*_examples.py" ${TEST_FLAGS}

requirements:
	rm -f requirements.txt
	python setup.py --name

html:
	cd sphinx && make html

examples:
	cd sphinx && make examples

docs: html
	cd sphinx && make commit && make push

json:
	cd omas/utilities && python build_json_structures.py
	make cocos

cocos:
	cd omas/utilities && python generate_cocos_signals.py

tag:
	git tag -a v$$(cat omas/version) $$(git log --pretty=format:"%h" --grep="^version $$(cat omas/version)") -m "version $$(cat omas/version)"
	git push --tags

sdist:
	rm -rf dist
	python setup.py sdist

pypi: sdist
	python -m twine upload --repository pypi dist/*

testpypi:
	python -m twine upload --repository testpypi dist/*
	@echo install with:
	@echo pip install --index-url https://test.pypi.org/simple/ omas

release: tests requirements json cocos docs tag
	@echo 'Make release done'

.PHONY: site-packages

site-packages:
	pip install --upgrade --target ./site-packages -r requirements.txt
	@echo "for TCSH: setenv PYTHONPATH $$PWD/site-packages:\$$PYTHONPATH"
	@echo "for BASH: export PYTHONPATH=$$PWD/site-packages:\$$PYTHONPATH"
