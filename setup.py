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
        'aerofiles~=1.4.0',
        'beautifulsoup4~=4.6.0',
        'pyproj>=3.4.1',
        'geojson>=3.0.0',
        'shapely>2.0.0',
    ]
)
