from setuptools import setup, find_packages
from os.path import join, dirname, basename

with open('requirements.txt') as f:
    lines = f.read().splitlines()

# Split the requirements and the editable (-e) dependencies
requirements = [line for line in lines if not line.startswith("-e")]
dependency_links = [line.split("-e ")[-1] for line in lines if line.startswith("-e")]

setup(
    name=basename(dirname(__file__)),
    version='0.1',
    packages=find_packages(),
    install_requires=requirements,
    dependency_links=dependency_links
)