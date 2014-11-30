# -*- coding: utf-8 -*-

# vim: tabstop=4 shiftwidth=4 autoindent noexpandtab

PYTHON=`which python`
NAME=`python setup.py --name`

all: check 

#init:
#	pip install -r requirements.txt --use-mirrors

#dist: source deb

source:
	pandoc -f markdown_github -t plain -o README.txt README.md
	$(PYTHON) setup.py sdist
	rm -rf rax_autoscaler.egg-info

upload: source
	$(PYTHON) setup.py sdist upload

#deb:
#	$(PYTHON) setup.py --command-packages=stdeb.command bdist_deb

#rpm:
#	$(PYTHON) setup.py bdist_rpm --post-install=rpm/postinstall --pre-uninstall=rpm/preuninstall

#test:
#	unit2 discover -s tests -t .
#	python -mpytest weasyprint
#	nosetests

check:
	find . -name \*.py | grep -v 'docs/conf.py' | xargs pep8
	# find . -name \*.py | grep -v "^test_" | xargs pylint --errors-only --reports=n
	# pyntch
	# pyflakes
	# pychecker
	# pymetrics

clean:
	rm -rf build/ MANIFEST dist build rax_autoscaler.egg-info deb_dist
	find . -name '*.pyc' -delete
	rm README.txt
	$(PYTHON) setup.py clean

#doc:
# Generate Sphinx documentation.
doc:
	cd docs && make clean && make html 
