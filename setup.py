from setuptools import setup, find_packages

setup(
    name="bubblejail",
    version="0.1a",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'bubblejail = bubblejail.bubblejail:main'
        ],
    },
)
