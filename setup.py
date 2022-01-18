import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
  name = 'cbtool',


  version = '3.0.5',
  author = 'Marcio Silva, Michael Galaxy',
  author_email = 'cbtool-admin@googlegroups.com',
  description = 'CloudBench: Cloud Rapid Experimentation and Analysis Toolkit',
  long_description=long_description,
  long_description_content_type="text/markdown",
  url = 'https://github.com/ibmcb/cbtool',

  python_requires='>=3.6',

  # Currently, the only thing we provided on PyPi is the core library.
  # Getting a fully-fledged instance of CB installed will require
  # a proper DEB to be prepared. This just solves the issue of talking
  # talking to the cloudbench API using an already-installed version
  # of cloudbench. 

  packages = ['cbtool', 'cbtool/lib', 'cbtool/lib/api', 'cbtool/lib/auxiliary', 'cbtool/lib/clouds', 'cbtool/lib/operations', 'cbtool/lib/remote', 'cbtool/lib/stores'],

  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3.6',
  ],
  download_url = 'https://github.com/ibmcb/cbtool/archive/3.0.tar.gz',
  keywords = ['cloudbench', 'cloud', 'benchmarking', "spec"],

  # Currently, we've only listed packages listed as `= pip`
  # from the PUBLIC_dependencies.txt file, because pip install
  # can only recursively attempt to install pip-registered projects.
  # If we want to enable *all* dependencies, we're going to have to fork
  # and register cbtool-needed projects under the CloudBench user account on PyPi.
  install_requires = [
          'prettytable',
          'python-daemon',
          'twisted',
          'webob',
          'beaker',
          'python-redis',
          'pymongo',
          'pypureomapi',
          'python-novaclient',
          'python-neutronclient',
          'python-cinderclient',
          'python-glanceclient',
          'softlayer',
          'boto',
          'apache-libcloud',
          'docker',
          'pylxd',
          'pykube',
          'docutils',
          'markup',
          'pyyaml',
          'ruamel-yaml',
          'urllib3',
          'httplib2shim',
          'python-dateutil',
          'pillow',
          'jsonschema',
          'mysql-connector',
          'distro'
      ],
)
