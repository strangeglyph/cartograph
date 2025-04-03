from setuptools import setup

setup(
    name="cartograph",
    version="0.1.0",
    description="Hiking tracker",
    license="MIT",
    author="glyph",
    author_email="mail <at> strangegly <dot> ph",
    url="github.com/strangeglyph/cartograph",
    packages=["cartograph"],
    package_data={
      "cartograph": ['static/*', 'Templates/*', 'localization/*'],
    },
    install_requires=["flask", "dateparser"]
)
