from distutils.core import setup
from Cython.Build import cythonize
from distutils.extension import Extension
import numpy as np
import os

current_dir = os.path.dirname(os.path.abspath(__file__))


extensions = [
    Extension('project_utils.distance_in_structure.euclidean_cython',
              sources=["project_utils/distance_in_structure/euclidean_cython.pyx"],
              include_dirs=[np.get_include()] + [os.path.join(current_dir, "project_utils", "distance_in_structure")],
              language='c++', extra_compile_args=["-std=c++11"], extra_link_args=["-std=c++11"]),
    Extension('project_utils.distance_in_structure.path_sprawl_cython',
              sources=["project_utils/distance_in_structure/path_sprawl_cython.pyx"],
              include_dirs=[np.get_include()] + [os.path.join(current_dir, "project_utils", "distance_in_structure")],
              language='c++', extra_compile_args=["-std=c++11"], extra_link_args=["-std=c++11"]),
    Extension('project_utils.distance_in_structure.sprawl_utils',
              sources=["project_utils/distance_in_structure/sprawl_utils.pyx"],
              include_dirs=[np.get_include()] + [os.path.join(current_dir, "project_utils", "distance_in_structure")],
              language='c++', extra_compile_args=["-std=c++11"], extra_link_args=["-std=c++11"]),
    Extension("project_utils.color_image.color_image", ["project_utils/color_image/color_image.pyx"],
        include_dirs = [np.get_include()],
              extra_compile_args=['-std=c++11'],
              language='c++',
              )
    ]

setup(
    ext_modules = cythonize(extensions),
    name="coloring image", requires=['numpy', 'matplotlib', 'tifffile', 'appdirs', 'SimpleITK', 'PyQt5', 'scipy',
                                     'qtawesome', 'six']
)