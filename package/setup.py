from setuptools import setup
import os, shutil

# package name
package = "searchbible"

# update package readme
latest_readme = os.path.join("..", "README.md") # github repository readme
package_readme = os.path.join(package, "README.md") # package readme
shutil.copy(latest_readme, package_readme)
with open(package_readme, "r", encoding="utf-8") as fileObj:
    long_description = fileObj.read()

# get required packages
install_requires = []
with open(os.path.join(package, "requirements.txt"), "r") as fileObj:
    for line in fileObj.readlines():
        mod = line.strip()
        if mod:
            install_requires.append(mod)

# https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/
setup(
    name=package,
    version="0.0.61",
    python_requires=">=3.8",
    description="Search Bible AI - Integrate Unique Bible App resources with AI tools",
    long_description=long_description,
    author="Eliran Wong",
    author_email="support@letmedoit.ai",
    packages=[
        package,
        f"{package}.db",
        f"{package}.utils",
        f"{package}.icons",
        f"{package}.converter",
        f"{package}.data",
        f"{package}.data.bibles",
    ],
    package_data={
        package: ["*.*"],
        f"{package}.db": ["*.*"],
        f"{package}.utils": ["*.*"],
        f"{package}.icons": ["*.*"],
        f"{package}.converter": ["*.*"],
        f"{package}.data": ["*.*"],
        f"{package}.data.bibles": ["*.*"],
    },
    license="GNU General Public License (GPL)",
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            f"{package}={package}.{package}:main",
            f"{package}converter={package}.{package}converter:main",
        ],
    },
    keywords="ai unique bible search openai google chatgpt gemini chromadb",
    url="https://letmedoit.ai",
    project_urls={
        "Source": f"https://github.com/eliranwong/{package}ai",
        "Tracker": f"https://github.com/eliranwong/{package}ai/issues",
        "Documentation": f"https://github.com/eliranwong/{package}ai/wiki",
        "Funding": "https://www.paypal.me/MarvelBible",
    },
    classifiers=[
        # Reference: https://pypi.org/classifiers/

        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: End Users/Desktop',
        'Topic :: Utilities',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
