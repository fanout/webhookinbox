API
===

Introduction
------------

WebhookInbox is a web service and website that receives HTTP requests from external sources and stores the data of those requests for later retrieval. This document describes WebhookInbox's HTTP-based API, which enables programmatic manipulation of inboxes. You can use the API to create and destroy inboxes, retrieve items from inboxes, and listen for newly-added items in realtime.

All HTTP API calls are made to ``api.webhookinbox.com``.

Inboxes
-------

Inboxes store a list of request items. Each inbox has a unique id and target URL. Requests made against an inbox's target URL are captured and the data is stored in the inbox. WebhookInbox responds to HTTP requests automatically, using status code 200.

Inboxes have a limit of 100 items. If many requests are received in rapid succession, then this limit is raised to a larger value to ensure clients monitoring the inbox don't miss any data. However, once traffic dies down then items will be truncated back to 100.

Items
-----

In the API, request items are represented as JSON objects with the following fields:

  * ``id`` - A unique id for the item within the inbox.
  * ``type`` - Either "normal" or "hub-verify". The latter value is used if the request was handled by WebhookInbox as a PubSubHubbub verification request.
  * ``method`` - The request method (e.g. "GET", "POST", etc).
  * ``path`` - The path of the request URI. This will always be ``/i/{id}/`` where {id} is the inbox id. The query string is not included as part of the path.
  * ``query`` - The query string of the request URI.
  * ``headers`` - A list of headers, where each header is itself a list containing two strings. The first string in the list is the name of the header, and the second string is the header's value. For example, a header in the list might be represented as ["Content-Type", "text/html"].
  * ``body`` - The body of the request as text. If this field is present, then the ``body-bin`` field will not be present.
  * ``body-bin`` - The body of the request as base64-encoded binary. If this field is present, then the ``body`` field will not be present. This field is only used if the body does not contain valid text.
  * ``created`` - The date and time that the request was received, in ISO 8601 format.
  * ``ip_address`` - The IP address of the client making the request.

For example, an item in the inbox might look like::

  {
    "id": "8",
    "type": "normal",
    "method": "POST",
    "path": "/i/vJ2lWRKY/",
    "query": "techcrunch",
    "headers": [
      ["Content-Length", "9615"],
      ["Content-Type", "application/atom+xml; charset=UTF-8"],
      ["User-Agent", "WordPress/PuSHPress 0.1.7.1"],
      ...
    ],
    "body": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><feed ...>...</feed>",
    "created": "2013-06-10T02:24:21.638223",
    "ip_address": "50.18.211.204"
  }

(format trimmed for readability)

Query strings
-------------

Requests made to an inbox's target URL can use any value for the query part. For example, if there exists an inbox with id ``vJ2lWRKY`` and target URL ``http://api.webhookinbox.com/i/vJ2lWRKY/in/``, then requesting any of the following URLs would cause the data to be captured into the same inbox:

  * ``http://api.webhookinbox.com/i/vJ2lWRKY/in/``
  * ``http://api.webhookinbox.com/i/vJ2lWRKY/in/?hello``
  * ``http://api.webhookinbox.com/i/vJ2lWRKY/in/?a=1&b=2``

By varying the query string, there can be an unlimited number of unique URLs that all funnel into the same inbox. If the inbox target URL is being registered/subscribed to several HTTP callback services, then a different query part can be used for each subscription. This way, the ``query`` field of items in the inbox can be used to differentiate which requests came from which services.

Expiration
----------

Each inbox also has a time-to-live (TTL) value. If an inbox is not refreshed within this period of time, then the inbox is automatically destroyed. An inbox can be refreshed explicitly by making a call to the ``/refresh/`` endpoint, or implicitly by retrieving items. If an inbox is intended for a temporary browsing session, then it should have a low TTL so that it will be cleaned up in case the user navigates away. An inbox being used for long term network inspection could of course have a large TTL.

Inboxes may also be explicitly destroyed without waiting for expiration.

PubSubHubbub
------------

Normally, when a request is made to an inbox target URL, WebhookInbox responds with the string "Ok". However, if the request is detected to be a PubSubHubbub verification request, then WebhookInbox will respond appropriately such that the verification succeeds. This means it is possible to use an inbox target URL as the callback of a PubSubHubbub subscription request, and receive feed updates into the inbox.

Creating, refreshing, destroying
--------------------------------

To create an inbox, make a POST request to the ``/create/`` resource::

  POST /create/ HTTP/1.1

This will yield a response such as::

  HTTP/1.1 200 OK
  Content-Type: application/json

  {
    "id": "vJ2lWRKY",
    "base_url": "http://api.webhookinbox.com/i/vJ2lWRKY/",
    "ttl": 3600
  }

The ``base_url`` field is the URL of the resource representing the inbox. Other endpoints related to the inbox are suffixed to the base URL. Notably, the inbox target URL is the base URL suffixed with ``in/``. Requests made to the target URL will have their data captured and stored in the inbox. The ``ttl`` value specifies a duration in seconds, so in this example the inbox has a TTL of 1 hour.

Optionally, you can ask for a specific TTL by providing one as a post parameter::

  POST /create/ HTTP/1.1
  Content-Type: application/x-www-form-urlencoded

  ttl=300

The service should then honor your request as such::

  HTTP/1.1 200 OK
  Content-Type: application/json

  {
    "id": "vJ2lWRKY",
    "base_url": "http://api.webhookinbox.com/i/vJ2lWRKY/",
    "ttl": 300
  }

If an inbox should survive longer than its TTL, then it will need to be periodically refreshed::

  POST /i/vJ2lWRKY/refresh/ HTTP/1.1

The server will respond with a status of 200 if the inbox was successfully refreshed. This means the TTL countdown has restarted. It is also possible to change the TTL by providing a ``ttl`` post parameter when refreshing.

Inboxes are also implicitly refreshed when fetching items. See the `Retrieving items`_ section.

To destroy an inbox, make a DELETE request to the inbox base URL::

  DELETE /i/vJ2lWRKY/ HTTP/1.1

On successful destruction, the server will respond with a status of 200.

Retrieving items
----------------

To retrieve past items or check for new ones, a GET is made to the ``/items/`` endpoint of an inbox. This endpoint supports the following parameters:

  * ``order`` - Either "created" or "-created", to retrieve items in ascending order (starting from the oldest item) or descending order (starting from the most recent item).
  * ``max`` - Limit the amount of returned items to this number.
  * ``since`` - Return items after this position specification. The format of this parameter is a position spec type followed by a colon and then a value. There are two position spec types supported: ``id`` and ``cursor``.
  
For example, to request the most recent 20 items, do::

  GET /i/vJ2lWRKY/items/?order=-created&max=20 HTTP/1.1

The server will respond with up to 20 items, most recent first::

  HTTP/1.1 200 OK
  Content-Type: application/json

  {
    "items": [
      { .. item ... },
      { .. item ... },
      { .. item ... },
      ...
    ],
    "last_cursor": "41"
  }

(response trimmed for readability)

The ``last_cursor`` field appears if there are more items in the inbox beyond what has been returned. A subsequent request can be made against this value to retrieve the next items. For example, here's a request to get the next 20::

  GET /i/vJ2lWRKY/items/?order=-created&since=cursor:41&max=20 HTTP/1.1

The response to this request may again contain another ``last_cursor`` field, and this process may be repeated to traverse further into the inbox. If a response contains no ``last_cursor`` field, then it means the end of the inbox has been reached.

Setting ``order`` to "created" can be used to traverse forward in the inbox. This is primarily used to retrieve newly added items, and the request will long-poll (hang open) waiting for new items if there aren't any to immediately return. For example, here's a request for the 20 oldest items of the inbox::

  GET /i/vJ2lWRKY/items/?order=created&max=20 HTTP/1.1

The server will respond with up to 20 items, oldest first::

  HTTP/1.1 200 OK
  Content-Type: application/json

  {
    "items": [
      { .. item ... },
      { .. item ... },
      { .. item ... },
      ...
    ],
    "last_cursor": "41"
  }

(response trimmed for readability)

Just as when requesting for items in "-created" order, requesting for items in "created" order may also result in a response containing a ``last_cursor`` value. This value can be used in a subsequent request to retrieve the next items. Unlike with "-created" order, though, the "created" order **always** returns a ``last_cursor`` value, since there may always be new items forward in time.

Finally, items can be requested after a given item id. This is the most appropriate way to query for new items after making a request for items in "-created" order. For example, if the newest item has id "63", then checking for new items can be done like this::

  GET /i/vJ2lWRKY/items/?order=created&since=id:63 HTTP/1.1

Again, when using "created" order, be aware that the request may hang open until new items are ready. Also, the response will contain a ``last_cursor`` value which should be used in subsequent requests (with since=cursor rather than since=id). More about this in the `Live updates`_ section.

Live updates
------------

There are two ways to receive updates of new items:

  1. Using the ``/items/`` endpoint to check for items after the newest item, resulting in HTTP long-polling (server holds request open until items are ready and then makes a full response).
  2. Using the ``/stream/`` endpoint to receive events of new items, resulting in HTTP streaming (server appends to response indefinitely).

The HTTP long-polling mechanism is the most robust and is ideal for browser applications. First, make an initial request against the last known item::

  GET /i/vJ2lWRKY/items/?order=created&since=id:63 HTTP/1.1

The response will contain a ``last_cursor`` value. From that point on, repeatedly request against the last known cursor::

  GET /i/vJ2lWRKY/items/?order=created&since=cursor:63 HTTP/1.1

Always use the ``last_cursor`` value from the most recent response in the next request.

The HTTP streaming mechanism first responds with the text "[opened]" followed by a newline. Then, any new items are returned as a single line of JSON followed by a newline. This mechanism can be handy for monitoring with curl::

  $ curl http://api.webhookinbox.com/i/vJ2lWRKY/stream/
  [opened]
  { ... item ... }
  { ... item ... }

Non-browser applications may prefer using the streaming mechanism because the HTTP connection doesn't need to be closed after every received item. However, be aware that if the inbox needs to be refreshed to avoid expiration then the application must make refresh requests independently of the open stream. Simply having a stream open does not prevent the inbox from expiring. With the long-polling mechanism, on the other hand, the inbox ends up getting refreshed each time the client polls.

Contact
-------

WebhookInbox is produced by Fanout, Inc. Please do not hesitate to contact info@fanout.io with any questions.
