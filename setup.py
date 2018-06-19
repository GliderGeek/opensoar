from setuptools import setup, find_packages

exec(open('opensoar/version.py').read())

with open("README.rst", "r") as f:
    long_description = f.read()

setup(
    name='opensoar',
    version=__version__,  # has been import above in exec command
    license='MIT',
    description='Open source python library for glider flight analysis',
    url='https://github.com/glidergeek/opensoar',
    packages=find_packages(exclude=['tests']),
    long_description=long_description,
    install_requires=[
        'pygeodesy>=17.11.26',
        'aerofiles>=0.4.1',
        'beautifulsoup4>=4.6.0'
    ]
)
