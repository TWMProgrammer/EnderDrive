from setuptools import setup, find_packages

setup(
    name="enderdrive",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        # Add other dependencies as needed
    ],
)