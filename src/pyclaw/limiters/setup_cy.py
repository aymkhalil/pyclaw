from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
import numpy

extensions=[Extension("tvd_cy",["tvd_cy.pyx"])]

setup(
    ext_modules = cythonize(extensions),
    include_dirs=[numpy.get_include()]
)
