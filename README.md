WebhookInbox
============

Authors: Justin Karneges <justin@fanout.io>, Katsuyuki Ohmuro <harmony7@pex2.jp>  
Mailing List: http://lists.fanout.io/listinfo.cgi/fanout-users-fanout.io

WebhookInbox is a web service and website that receives HTTP requests from external sources and stores the data of those requests for later retrieval. Each inbox is represented by a generated URL, which can be passed to other applications for use. If you're developing a service that makes HTTP callbacks, WebhookInbox can be used as a convenient way to examine what you're sending. Incoming request data is displayed on the WebhookInbox website in realtime as it happens. There is also a REST API available, meaning WebhookInbox can be used programmatically, for example by a browser app wishing to receive HTTP callbacks.

There is an instance of WebhookInbox running at http://webhookinbox.com/ for anyone to use.

License
-------

WebhookInbox is offered under the MIT license. See the COPYING file.

Requirements
------------

  * redis
  * pushpin (or fanout.io)
  * a web server

Setup
-----

WebhookInbox is a Django App. Set it up with virtualenv like this:

    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

Create a .env file in the webhookinbox base directory, to hold environment variables:

    API_BASE=http://api.localhost:8000

Make an entry for "api.localhost" in /etc/hosts pointing to localhost, e.g.:

    127.0.0.1 localhost api.localhost

Run the server:

    python manage.py runserver

You should then be able to browse to http://localhost:8000/ and use the service, without realtime updates.

Realtime updates
----------------

To enable realtime updates, install the [Pushpin](http://pushpin.org/) proxy server. By default, Pushpin listens on port 7999 for client requests, 5561 for control requests, and uses key "changeme". Add GRIP_URL to your .env file and also change the API_BASE:

    GRIP_URL=http://localhost:5561?key=changeme
    API_BASE=http://api.localhost:7999

Make sure the Pushpin routes file is configured to route to port 8000 and use Auto Cross-Origin. You should have a line in the routes file like this:

    *,aco localhost:8000

Now restart the server and browse to http://localhost:8000/

Cleanup task
------------

WebhookInbox has a cleanup command that should be run once per minute, to prune items and inboxes, and also to timeout requests that were expecting custom responses.

You can run the command at anytime like this:

    python manage.py cleanup

Stick it in cron:

    * * * * * cd /path/to/webhookinbox && source venv/bin/activate && python manage.py cleanup >/dev/null 2>&1
