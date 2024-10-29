from setuptools import setup

version = {}
with open("melee/version.py") as fp:
    exec(fp.read(), version)

setup(
    name = 'melee',
    packages = ['melee'],
    install_requires=[
        'pyenet@git+https://github.com/piqueserver/pyenet',
        'py-ubjson',
        'numpy',
        'pywin32; platform_system=="Windows"',
        'packaging'
    ],
    python_requires='>=3.9',
    version = version['__version__'],
    description = 'Open API written in Python 3 for making your own Smash Bros: Melee AI that works with Slippi Online',
    author = 'AltF4',
    author_email = 'altf4petro@gmail.com',
    url = 'https://github.com/altf4/libmelee',
    download_url = 'https://api.github.com/repos/libmelee/libmelee/tarball',
    keywords = ['dolphin', 'AI', 'video games', 'melee', 'smash bros', 'slippi'],
    classifiers = [],
    license = "LGPLv3",
    include_package_data=True,
)
