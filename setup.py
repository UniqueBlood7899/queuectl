from setuptools import setup, find_packages

setup(
    name='queuectl',
    version='1.0.0',
    py_modules=['cli', 'job', 'queue_manager', 'worker', 'storage', 'config', 'utils'],  # Changed 'queue' to 'queue_manager'
    install_requires=[
        'click>=8.0.0',
        'tabulate>=0.9.0',
    ],
    entry_points={
        'console_scripts': [
            'queuectl=cli:cli',
        ],
    },
    python_requires='>=3.7',
)