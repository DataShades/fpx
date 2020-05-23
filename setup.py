from setuptools import setup, find_packages
from glob import glob

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = [
    "asyncblink==0.3.2",
    "sqlalchemy~=1.0",
    "alembic~=1.4",
    "sanic~=20.3",
    "sanic-cors~=0.10.0",
    "aiohttp[speedups]~=3.6",
    "click~=7.1.2",
]
entry_points = {"console_scripts": ["fpx = fpx.cli:fpx"]}

setup(
    name="fpx",
    version="0.0.0dev4",
    description="""""",
    long_description=long_description,
    author="Sergey Motornyuk",
    license="AGPL",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        # 3 - Alpha
        # 4 - Beta
        # 5 - Production/Stable
        "Development Status :: 3 - Alpha",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Programming Language :: Python :: 3.8",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=install_requires,
    entry_points=entry_points,
    package_data={
        '': ['alembic.ini', 'migrations/**/*']
    }
        # ('', ['data/alembic.ini']),
        # ('migrations', ),
        # ('migrations/versions', glob('data/migrations/versions/*.py')),

)
