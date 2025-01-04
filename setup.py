from setuptools import setup, find_packages

with open("requirements.txt") as f:
    required_packages = f.read().splitlines()

with open("README.md") as f:
    long_description = f.read()

setup(
    name="translatevideo",
    version="1.0.0",
    description="Bulk Generate SRT Files From Video Using Argos Translate",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="M. J. Bourquin",
    author_email="",
    url="",
    packages=find_packages(),
    install_requires=required_packages,
)
