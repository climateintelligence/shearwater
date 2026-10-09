.. _installation:

Installation
============

.. contents::
    :local:
    :depth: 1

Install from Conda
------------------

.. warning::

   TODO: Prepare Conda package.

Install from GitHub
-------------------

Check out code from the ShearWater GitHub repo and start the installation:

.. code-block:: console

   $ git clone https://github.com/cehbrecht/shearwater.git
   $ cd shearwater

Create Conda environment named `shearwater`:

.. code-block:: console

   $ conda env create -f environment.yml
   $ source activate shearwater

Install ShearWater app:

.. code-block:: console

  $ pip install -e .
  OR
  make install

For development you can use this command:

.. code-block:: console

  $ pip install -e .[dev]
  OR
  $ make develop

Start ShearWater PyWPS service
------------------------------

After successful installation you can start the service using the ``shearwater`` command-line.

.. code-block:: console

   $ shearwater --help # show help
   $ shearwater start  # start service with default configuration

   OR

   $ shearwater start --daemon # start service as daemon
   loading configuration
   forked process id: 42

The deployed WPS service is by default available on:

http://localhost:5000/wps?service=WPS&version=1.0.0&request=GetCapabilities.

.. NOTE:: Remember the process ID (PID) so you can stop the service with ``kill PID``.

You can find which process uses a given port using the following command (here for port 5000):

.. code-block:: console

   $ netstat -nlp | grep :5000


Check the log files for errors:

.. code-block:: console

   $ tail -f  pywps.log

... or do it the lazy way
+++++++++++++++++++++++++

You can also use the ``Makefile`` to start and stop the service:

.. code-block:: console

  $ make start
  $ make status
  $ tail -f pywps.log
  $ make stop


Run ShearWater as Docker container
----------------------------------

You can also run ShearWater as a Docker container.

.. warning::

  TODO: Describe Docker container support.

Use Ansible to deploy ShearWater on your System
-----------------------------------------------

Use the `Ansible playbook`_ for PyWPS to deploy ShearWater on your system.

Use the Linux deployment specification in the deployment inventory::

  conda_env_use_spec: true
  conda_env_spec_file: linux-64.spec

``linux-64.spec`` replaces the old ``spec-list.txt`` and uses the filename
expected by the current playbook. Update inventories that explicitly
override the filename with ``spec-list.txt``. Run a full environment
deployment; an application-only update does not update Conda packages.

The Linux spec includes the playbook's additional packages: Gunicorn,
gevent, psycopg2 2.9.12, DRMAA 0.7.9, dill, pytest and pytest-cov.
The separate ``spec-file.txt`` is a historical macOS ARM snapshot and must
not be used for Linux deployments.

ShearWater requires Python 3.10 or 3.11 and PyWPS 4.7. TensorFlow stays on
the 2.15 series with NumPy 1.x for compatibility with the bundled Keras
models. TensorFlow is installed with pip: its Conda 2.15 package pins an
older ICU library that conflicts with the playbook's PostgreSQL client.
The playbook installs TensorFlow through ShearWater's ``pip install .``
step after creating the environment from ``linux-64.spec``. When creating
an environment directly from ``environment.yml``, its pip section performs
this step. The explicit spec only locks Conda packages; the pip dependencies
are governed by ``requirements.txt``. Conda also installs the native Metview
executable required by the Python bindings.


.. _Ansible playbook: http://ansible-wps-playbook.readthedocs.io/en/latest/index.html
