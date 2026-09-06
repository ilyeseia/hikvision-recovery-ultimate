from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="hikvision-recovery",
    version="0.1.0",
    author="Hikvision Recovery Team",
    author_email="recovery@hikvision.local",
    description="Professional ISAPI client for Hikvision DVR/NVR management and recording recovery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/hikvision-recovery",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Security Professionals",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Recovery Tools",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.7.0",
            "pre-commit>=3.5.0",
        ],
        "sdk": [
            "ctypesgen>=1.1.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "hikvision = hikvision_recovery.cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)