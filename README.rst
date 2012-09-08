HelpIM 3.1
==========

Installation (Development)
++++++++++++++++++++++++++

These are preliminary instructions for how to setup a development
environment. This code is not meant to be used in production yet.


Prerequisites:
--------------

To setup a development environment, HelpIM needs Python, mysql (including
mysql_config, wich usually part of a mysql client development package) and
the Tigase jabber server.

To use all functionality of HelpIM, it is best to use Tigase 4.3.1. Versions
before 4.2 don't support HelpIMs chat state notification. The 5.x versions are
not tested with HelpIM. Tigase needs needs a JDK (not JRE!) of version 1.6 or
higher.

On a Debian system the needed python and mysql packages are:

    git-core python python-dev mysql-server mysql-client libmysqlclient-dev libxml2-dev openjdk-6-jre-headless

Installation:
-------------

1) Download the app with git::

    $ git clone git://github.com/e-hulp/HelpIM.git

2) Download dependencies like this::

    $ cd HelpIM
    $ python bootstrap.py --distribute
    $ ./bin/buildout

  HelpIM runs on django 1.3 by default, if you want another version (say
  1.2.1), run::

    $ ./bin/buildout versions:django=1.2.1

4) Create a mysql database (and a user with full access rights)

5) Copy the development settings template::

    $ cp helpim/development.py{.example,}

6) Edit the development settings at ``helpim/development.py`` and make
   ``DATABASES`` match your DB settings

7) Initialize the DB::

    $ ./bin/manage.py syncdb

  At that point you will be asked to create a first admin user. Remember
  those credentials they are essential.

  After initializing the DB, you must update it to the latest changes:

    $ ./bin/manage.py migrate

8) Load the standard permissions and other standard data into the DB::

    $ ./bin/manage.py loaddata setup_data

9) Run the dev server::

    $ ./bin/manage.py runserver

10) Point your browser to http://localhost:8000/admin and login with the
    credentials from above.

11) If you want to test the chat too, and you have tigase running::

    Open a new terminal and run:

    $ ./bin/proxy.py 8888

    and point your browser to http://localhost:8888/admin

    The proxy redirects XMPP-BOSH requests on
    http://localhost:8888/http-bind/
    to tigase on http://localhost:5280/http-bind/
    and all other requests to http://localhost:8000/

Updating the setup data (Development)
++++++++++++++++++++++++++++++++++++++

With the command::

    django-admin.py hi_dump_settings --indent=4 > helpim/fixtures/setup_data.json

you can update the setup_data to the changes you have made in the
settings stored in the database. These changes can now be imported
by other developers. Use the 'load_data' command to import them into
a newly created database. If you want to merge them into an already
existing database, you can use the 'hi_load_settings'.

.. note:: There is deliberately chosen to not use 'initial_data.json', to avoid
          overwriting data when running syncdb.


Adding content with flatpages
+++++++++++++++++++++++++++++

Static content in HelpIM installations can be added through Django the
flatpages application. Admins should see the administration panel in the admin
interface.

Adding content to public-facing web pages comes with very few restrictions:
When creating the flatpage choose a non-colliding URL, and make sure not to
check the "[ ] Registration required" box.

When adding content that is only available to staff members (such as news,
manuals, guidelines, etc.) you need to prefix the URL with "/admin/" and check
the "[x] Registration required" box, so it is not publicly visible.

For both types of contents, make sure the url contains leading and trailing
slashes. All content will automatically be linked to from the particular
navigation bar.
