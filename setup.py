from setuptools import setup, find_packages

setup(
    name='opensoar',
    version='0.1.0',
    license='MIT',
    description='Open source python library for glider flight analysis',
    url='https://github.com/glidergeek/opensoar',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'pygeodesy>=17.11.26',
        'aerofiles>=0.4.1',
        'beautifulsoup4>=4.6.0'
    ]
)
