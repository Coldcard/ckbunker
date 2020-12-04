# Copyright 2020 by Coinkite Inc. This file is covered by license found in COPYING-CC.
#
# based on <http://click.pocoo.org/5/setuptools/#setuptools-integration>
#
# To use this, install with:
#
#   pip install --editable .

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='bunker',
    version='0.1',
    license='MIT+CC',
    python_requires='>=3.7.0',
    url='https://github.com/Coldcard/ckbunker',
    author='Coinkite Inc.',
    author_email='support@coinkite.com',
    description="Submit PSBT files automatically to your Coldcard for signing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[      # see requirements.txt tho.
        'Click',
        'stem',
        'aiohttp',
        'aiohttp-jinja2',
        'ckcc-protocol>=1.0.0',
    ],
    entry_points='''
        [console_scripts]
        ckbunker=main:main
    ''',
    classifiers=[
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS :: MacOS X',
    ],
)

