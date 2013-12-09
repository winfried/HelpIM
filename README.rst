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
a XMPP server that supports BOSH, SASL ANOUNYMOUS and chat state notifications
in a MUC. Right now Tigase 4.3.1 and higher and Prosody support these. HelpIM
is tested with Prosody.

On a Debian system the needed python and mysql packages are::

    git-core python python-dev mysql-server mysql-client libmysqlclient-dev libxml2-dev openjdk-6-jre-headless

Installation:
-------------

1) Download the app with git::

    $ git clone git://github.com/e-hulp/HelpIM.git

2) Download dependencies like this::

    $ cd HelpIM
    $ python bootstrap.py --distribute
    $ ./bin/buildout

   If you encouter problems with the version of setuptools or distribute,
   then you may substitute the bootstrap command with::

    $ python bootstrap.py --distribute -v 2.1.11

   This will pin to a version that will not have these problems.

   HelpIM runs on django 1.3 by default, if you want another version (say
   1.2.1), run::

    $ ./bin/buildout versions:django=1.2.1

3) Create a mysql database (and a user with full access rights)

4) Copy the development settings template::

    $ cp helpim/development.py{.example,}

5) Edit the development settings at ``helpim/development.py`` and make
   ``DATABASES`` match your DB settings
   Note: HelpIM does not support the MySQL Innodb engine. Pleas use MyISAM.


6) Initialize the DB::

    $ ./bin/manage.py syncdb

   At that point you will be asked to create a first admin user. Remember
   those credentials they are essential.

   After initializing the DB, you must update it to the latest changes:

    $ ./bin/manage.py migrate

7) Load the standard permissions and other standard data into the DB::

    $ ./bin/manage.py loaddata setup_data

8) Run the dev server::

    $ ./bin/manage.py runserver

9) Point your browser to http://localhost:8000/admin and login with the
    credentials from above.

10) If you want to test the chat too, and you have tigase running::

    Open a new terminal and run::

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

Updating the translations (Development)
+++++++++++++++++++++++++++++++++++++++

Before updating the translations, make shure the buddychat is activated. Failing
to do so may result in the translation system not picking up the buddychat specific
translations.

To update the translations files::

    $ cd helpim
    $ ../bin/manage.py makemessages -a -e ".html" -e ".txt"
    $ ../bin/manage.py makemessages -a -d djangojs

Now check the language files for changes. Once the translations are updated, you have
to compile the messages::

    $ ../bin/manage.py compilemessages

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
