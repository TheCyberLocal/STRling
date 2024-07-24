# pip install setuptools wheel twine
# python setup.py sdist bdist_wheel
# twine upload dist/*
from setuptools import setup, find_packages


with open('./docs/pypi_docs.md', 'r') as f:
    description = f.read()

setup(
    name='STRling',
    version='2.5.3',
    packages=find_packages(),
    install_requires=[
        # Add dependencies here.
        # e.g. 'numpy>=1.11.1'
    ],
    long_description=description,
    long_description_content_type='text/markdown',
)
