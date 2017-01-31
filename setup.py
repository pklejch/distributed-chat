from setuptools import setup, find_packages
 
 
with open('README.md') as f:
    long_description = ''.join(f.readlines())
 
 
setup(
    name='distributedchat',
    version='0.9',
    description='.',
    long_description=long_description,
    author='Petr Klejch',
    author_email='klejcpet@fit.cvut.cz',
    keywords='distributed algorithm,chat,chang roberts',
    license='GPL-3.0',
    url='https://github.com/pklejch/distributed-chat',
    packages=find_packages(),
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: Implementation :: CPython',
        ],
    install_requires=['click>=6', 'cryptography'],
    setup_requires=['pytest-runner','pytest'],
    tests_require=['pytest', 'configparser'],
    entry_points={
        'console_scripts': [
            'distributedchat = distributedchat.chat:main',
        ],
    },
    package_data={
        'distributedchat': ['keys.cfg','main.ui','startnode.ui']
    },
)
