import re
from setuptools import setup


with open('README.md', encoding='utf-8') as fp:
    readme = fp.read()

with open('requirements.txt') as fp:
    requirements = fp.readlines()

with open('pilmoji/__init__.py') as fp:
    contents = fp.read()

    try:
        version = re.search(
            r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', contents, re.M
        ).group(1)
    except AttributeError:
        raise RuntimeError('Could not identify version') from None

    try:
        author = re.search(
            r'^__author__\s*=\s*[\'"]([^\'"]*)[\'"]', contents, re.M
        ).group(1)
    except AttributeError:
        author = 'jay3332'


setup(
    name='pilmoji-cached',
    author=author,
    url='https://github.com/amiralimollaei/pilmoji-cached',
    project_urls={
        "Issue tracker": "https://github.com/amiralimollaei/pilmoji-cached",
    },
    version=version,
    packages=['pilmoji'],
    license='MIT',
    description="Pilmoji-cached is an emoji renderer for Pillow, Python's imaging library.",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    install_requires=requirements,
    python_requires='>=3.8.0',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ]
)
