# -*- coding: utf-8 -*-

PYTHON=`which python`
NAME=`python setup.py --name`

all: check source

#init:
#	pip install -r requirements.txt --use-mirrors

#dist: source deb

source: clean
	pandoc -f markdown_github -t plain -o README.txt README.md
	$(PYTHON) setup.py sdist
	rm -rf RAX_AutoScaler.egg-info

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
	find . -name \*.py | xargs pep8
	# find . -name \*.py | grep -v "^test_" | xargs pylint --errors-only --reports=n
	# pyntch
	# pyflakes
	# pychecker
	# pymetrics

clean:
	$(PYTHON) setup.py clean
	rm -rf build/ MANIFEST dist build my_program.egg-info deb_dist
	find . -name '*.pyc' -delete
	rm -rf RAX_AutoScaler.egg-info
	rm README.txt
