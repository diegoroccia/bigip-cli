from setuptools import setup

setup(
    name='bigip',
    version='0.1',
    py_modules=['bigip'],
    install_requires=[
        'Click',
        'f5-sdk'
    ],
    entry_points='''
        [console_scripts]
        bigip=bigip:cli
    ''',
)
