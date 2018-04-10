try:
    import setuptools
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()

from setuptools import setup, find_packages

# Do not edit: The VERSION gets updated by the update-version script
VERSION = '0.1.48'

setup(
    name='gui_o_matic',
    version=VERSION,
    author='Mailpile ehf.',
    author_email='team@mailpile.is',
    url='https://github.com/mailpile/gui-o-matic/',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'gui-o-matic = gui_o_matic.__main__:main'
        ]},
    license='See LICENSE.txt',
    description='A cross-platform tool for minimal GUIs',
    long_description=open('README.md').read(),
    classifiers=[
        'Environment :: MacOS X',
# TODO: 'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Operating System :: MacOS :: MacOS X',
# TODO: 'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Topic :: Desktop Environment',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
    ]
)
