from pathlib import Path
from setuptools import setup, find_packages

here = Path(__file__).parent
readme = (here / "README.md").read_text(encoding="utf-8")

setup(
    name='STRling',
    version='2.5.4',
    packages=find_packages(),
    install_requires=[],
    long_description=readme,
    long_description_content_type='text/markdown',
    url="https://github.com/TheCyberLocal/STRling",
    project_urls={
        "Homepage": "https://github.com/TheCyberLocal/STRling",
        "Documentation": "https://github.com/TheCyberLocal/STRling/tree/main/docs",
        "Issues": "https://github.com/TheCyberLocal/STRling/issues",
    },
    author="TheCyberLocal",
    license="MIT",  # SPDX identifier; keeps setuptools happy
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.8",
)
