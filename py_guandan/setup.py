"""Compatibility shim for older pip/setuptools bundled with system Python."""

from setuptools import find_packages, setup


setup(
    name="py-guandan",
    version="0.2.0",
    description="Python Guandan core rules and bot development SDK.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.10",
    packages=find_packages(include=("guandan_core*", "guandan_bot*", "py_guandan*", "guandan_benchmark*")),
    extras_require={
        "websocket": ["websockets>=11"],
        "benchmark": ["requests>=2", "pyyaml>=6"],
        "dev": ["pytest>=7", "websockets>=11", "requests>=2", "pyyaml>=6"],
    },
)
