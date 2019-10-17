import os.path
import sys

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as build_ext


vi = sys.version_info
if vi < (3, 5):
    raise RuntimeError('httptools require Python 3.5 or greater')

CFLAGS = ['-O2']
ROOT = os.path.dirname(__file__)


class httptools_build_ext(build_ext):
    user_options = build_ext.user_options + [
        ('cython-always', None,
            'run cythonize() even if .c files are present'),
        ('cython-annotate', None,
            'Produce a colorized HTML version of the Cython source.'),
        ('cython-directives=', None,
            'Cythion compiler directives'),
        ('use-system-http-parser', None,
            'Use the system provided http-parser, instead of the bundled one'),
    ]

    boolean_options = build_ext.boolean_options + [
        'cython-always',
        'cython-annotate',
        'use-system-http-parser',
    ]

    def initialize_options(self):
        # initialize_options() may be called multiple times on the
        # same command object, so make sure not to override previously
        # set options.
        if getattr(self, '_initialized', False):
            return

        super().initialize_options()
        self.use_system_http_parser = False
        self.cython_always = False
        self.cython_annotate = None
        self.cython_directives = None

    def finalize_options(self):
        # finalize_options() may be called multiple times on the
        # same command object, so make sure not to override previously
        # set options.
        if getattr(self, '_initialized', False):
            return

        need_cythonize = self.cython_always
        cfiles = {}

        for extension in self.distribution.ext_modules:
            for i, sfile in enumerate(extension.sources):
                if sfile.endswith('.pyx'):
                    prefix, ext = os.path.splitext(sfile)
                    cfile = prefix + '.c'

                    if os.path.exists(cfile) and not self.cython_always:
                        extension.sources[i] = cfile
                    else:
                        if os.path.exists(cfile):
                            cfiles[cfile] = os.path.getmtime(cfile)
                        else:
                            cfiles[cfile] = 0
                        need_cythonize = True

        if need_cythonize:
            try:
                import Cython
            except ImportError:
                raise RuntimeError(
                    'please install Cython to compile httptools from source')

            if Cython.__version__ < '0.28':
                raise RuntimeError(
                    'httptools requires Cython version 0.28 or greater')

            from Cython.Build import cythonize

            directives = {}
            if self.cython_directives:
                for directive in self.cython_directives.split(','):
                    k, _, v = directive.partition('=')
                    if v.lower() == 'false':
                        v = False
                    if v.lower() == 'true':
                        v = True

                    directives[k] = v

            self.distribution.ext_modules[:] = cythonize(
                self.distribution.ext_modules,
                compiler_directives=directives,
                annotate=self.cython_annotate)

        super().finalize_options()

        self._initialized = True

    def build_extensions(self):
        if self.use_system_http_parser:
            self.compiler.add_library('http_parser')

            if sys.platform == 'darwin' and \
                    os.path.exists('/opt/local/include'):
                # Support macports on Mac OS X.
                self.compiler.add_include_dir('/opt/local/include')
        else:
            self.compiler.add_include_dir(
                    os.path.join(ROOT, 'vendor/http-parser'))
            self.distribution.ext_modules[0].sources.append(
                'vendor/http-parser/http_parser.c')

        super().build_extensions()


with open(os.path.join(ROOT, 'README.md')) as f:
    long_description = f.read()


with open(os.path.join(ROOT, 'httptools', '__init__.py')) as f:
    for line in f:
        if line.startswith('__version__ ='):
            _, _, version = line.partition('=')
            VERSION = version.strip(" \n'\"")
            break
    else:
        raise RuntimeError(
            'unable to read the version from httptools/__init__.py')


setup(
    name='httptools',
    version=VERSION,
    description='A collection of framework independent HTTP protocol utils.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/MagicStack/httptools',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Environment :: Web Environment',
        'Development Status :: 5 - Production/Stable',
    ],
    platforms=['POSIX'],
    author='Yury Selivanov',
    author_email='yury@magic.io',
    license='MIT',
    packages=['httptools', 'httptools.parser'],
    cmdclass={
        'build_ext': httptools_build_ext,
    },
    ext_modules=[
        Extension(
            "httptools.parser.parser",
            sources=[
                "httptools/parser/parser.pyx",
            ],
            extra_compile_args=CFLAGS,
        ),
    ],
    provides=['httptools'],
    include_package_data=True,
    test_suite='tests.suite'
)
