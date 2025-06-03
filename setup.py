#!/usr/bin/env python3
"""Setup script for awsx - AWS Super CLI"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aws-super-cli",
    version="0.1.0",
    author="Marcelo Acosta",
    author_email="your-email@example.com",
    description="AWS Super CLI - See your AWS resources across all accounts in one command",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marceloacosta/awsx",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "awsx=awsx.cli:app",
        ],
    },
    keywords="aws, cli, multi-account, devops, cloud, infrastructure",
    project_urls={
        "Bug Reports": "https://github.com/marceloacosta/awsx/issues",
        "Source": "https://github.com/marceloacosta/awsx",
    },
) 