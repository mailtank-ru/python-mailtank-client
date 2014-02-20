from setuptools import setup

from setuptools.command.test import test as TestCommand
import sys


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main('tests')
        sys.exit(errno)


setup(
    name='mailtank',
    version='0.0.1',
    description='Mailtank API Python client',
    url='https://github.com/mailtank-ru/python-mailtank-client',

    author='mailtank developers',
    author_email='anthony.romanovich@gmail.com',

    packages=['mailtank'],
    install_requires=['requests>=1.0.3', 'python-dateutil>=2.0'],
    tests_require=['pytest', 'httpretty', 'furl'],
    cmdclass = {'test': PyTest},
)
