all:
	@echo "No default"

tags:
	ctags -f .tags *.py */*.py

depends:
	pip install virtualenv
	bash -c 'source ENV/bin/activate &'
	pip install -r requirements.txt
	pip install --editable .
