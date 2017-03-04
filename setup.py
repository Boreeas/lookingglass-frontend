from setuptools import setup

setup(
    name="lookingglass",
    packages=["lookingglass"],
    include_package_data=True,
    version="0.0.1",
    install_requires=[
        "flask",
        "sqlalchemy",
        "psycopg2"
    ]
)