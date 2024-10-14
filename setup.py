from setuptools import setup, find_packages
from os.path import join, dirname, basename

setup(
    name=basename(dirname(__file__)),
    version='0.1',
    packages=find_packages(),
    install_requires=[],  # Leave this empty as conda will handle dependencies
    include_package_data=True,
    # Add any other necessary setup parameters here
)
