from setuptools import setup, find_packages
from os.path import join, dirname, basename

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name=basename(dirname(__file__)),
    version='0.1',
    packages=find_packages(),
    install_requires=requirements,
)
