from setuptools import setup, find_packages

setup(
    name="election-monitor-gui",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "tkinter",
        "matplotlib",
        "pandas",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "election-monitor=main:main"
        ]
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A GUI application to monitor election data.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/election-monitor-gui",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)