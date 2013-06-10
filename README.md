WebhookInbox
------------
Date: June 6th, 2013

Authors:
  * Justin Karneges <justin@fanout.io>
  * Katsuyuki Ohmuro <harmony7@pex2.jp>

Mailing List: http://lists.fanout.io/listinfo.cgi/fanout-users-fanout.io

WebhookInbox is a web service and website that receives HTTP requests from external sources and stores the data of those requests for later retrieval. Each inbox is represented by a generated URL, which can be passed to other applications for use. If you're developing a service that makes HTTP callbacks, WebhookInbox can be used as a convenient way to examine what you're sending. Incoming request data is displayed on the WebhookInbox website in realtime as it happens. There is also a REST API available, meaning WebhookInbox can be used programmatically, for example by a browser app wishing to receive HTTP callbacks.

There is an instance of WebHookInbox running at http://webhookinbox.com/ for anyone to use.

This project was heavily inspired by RequestBin: http://requestb.in/

License
-------

WebhookInbox is offered under the MIT license. See the COPYING file.

Requirements
------------

  * python django
  * redis
  * pushpin (or fanout.io)
  * python gripcontrol
  * a web server

Setup
-----

WebhookInbox is a Django App. An easy way to set things up is to use Apache, WSGI, and Pushpin. We'll assume you have everything installed and that your Django version is recent (1.4).

First, create a Django project and put the app inside:

    django-startproject wiproj
    mkdir wiproj/apps
    cd wiproj/apps
    git clone git://github.com/fanout/webhookinbox.git

Edit your settings.py so that Django knows how to find the app, by including something like this at the top:

    import os
    import sys

    PROJECT_ROOT = os.path.dirname(__file__)
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "../apps"))

Then add 'webhookinbox' to your INSTALLED_APPS. Also, make sure CsrfViewMiddleware is disabled (comment it out).

Additionally, set GRIP_PROXIES:

    from base64 import b64decode

    # pushpin and/or fanout.io is used for sending realtime data to clients
    GRIP_PROXIES = [
        # pushpin
        {
            'key: 'changeme', # make sure this matches with pushpin.conf
            'controlUri': 'http://localhost:5561'
        },
        # fanout.io
        #{
        #    'key': b64decode('your-realm-key'),
        #    'controlUri': 'http://api.fanout.io/realm/your-realm',
        #    'controlIss': 'your-realm'
        #}
    ]

In Apache's global configuration, set `WSGIPythonPath` to the base directory of the project. Then, create a virtual host with `WSGIScriptAlias` pointing to the wsgi.py file. E.g.:

    <VirtualHost *:8080>
        ServerName api.wi.yourdomain.com
        WSGIScriptAlias / /path/to/wiproj/wiproj/wsgi.py
        ...
    </VirtualHost>

That's enough for the API. If you want the website too, it's some static files you can serve using a separate virtual host:

    <VirtualHost *:8080>
        ServerName wi.yourdomain.com
        DocumentRoot /path/to/wiproj/apps/webhookinbox/html
        ...
    </VirtualHost>

Ensure Pushpin's `routes` file points to the port Apache is listening on:

    * localhost:8080

Finally, have cleanup.py scheduled to run periodically. It needs to be executed within a django context. The easiest way to do this is to create a wrapper shell script:

    #!/bin/sh
    export DJANGO_SETTINGS_MODULE="wiproj.settings"
    export PYTHONPATH=/path/to/wiproj
    python $*

Supposing the above script is named djrun.sh, then you could set up a cron entry to run every minute:

    * * * * * /path/to/djrun.sh /path/to/cleanup.py >/dev/null 2>&1
 
That should do it.
