##################
Resource endpoints
##################

.. _resource-endpoints:

GET /articles
=============

**Requires authentication**

Returns all records of the current user for this resource.

The returned value is a JSON mapping containing:

- ``items``: the list of records, with exhaustive attributes

A ``Total-Records`` header is sent back to indicate the estimated
total number of records included in the response.

A header ``Last-Modified`` will provide the current timestamp of the
collection (*see Server timestamps section*).  It is likely to be used
by client to provide ``If-Modified-Since`` or ``If-Unmodified-Since``
headers in subsequent requests.


Filtering
---------

**Single value**

* ``/articles?unread=true``

**Multiple values**

* ``/articles?status=1,2``

**Minimum and maximum**

Prefix attribute name with ``min_`` or ``max_``:

* ``/articles?min_word_count=4000``

:note:
    The lower and upper bounds are inclusive (*i.e equivalent to
    greater or equal*).

:note:
   ``lt_`` and ``gt_`` can also be used to exclude the bound.

**Exclude**

Prefix attribute name with ``not_``:

* ``/articles?not_status=0``

:note:
    Will return an error if a field is unknown.

:note:
    The ``Last-Modified`` response header will always be the same as
    the unfiltered collection.

Sorting
-------

* ``/articles?_sort=-last_modified,title``

.. :note:
..     Articles will be ordered by ``-stored_on`` by default (i.e. newest first).

:note:
    Ordering on a boolean field gives ``true`` values first.

:note:
    Will return an error if a field is unknown.


Counting
--------

In order to count the number of records, for a specific field value for example,
without fetching the actual collection, a ``HEAD`` request can be
used. The ``Total-Records`` response header will then provide the
total number of records.

See :ref:`batch endpoint <batch>` to count several collections in one request.


Polling for changes
-------------------

The ``_since`` parameter is provided as an alias for
``gt_last_modified``.

* ``/articles?_since=123456``

The new value of the collection latest modification is provided in
headers (*see Server timestamps section*).

When filtering on ``last_modified`` (i.e. with ``_since`` or ``_to`` parameters),
every deleted articles will appear in the list with a deleted status (``status=2``).

If the request header ``If-Modified-Since`` is provided, and if the
collection has not suffered changes meanwhile, a ``304 Not Modified``
response is returned.

:note:
   The ``_to`` parameter is also available, and is an alias for
   ``lt_last_modified`` (*strictly inferior*).


Paginate
--------

If the ``_limit`` parameter is provided, the number of items is limited.

If there are more items for this collection than the limit, the
response will provide a ``Next-Page`` header with the URL for the
Next-Page.

When there is not more ``Next-Page`` response header, there is nothing
more to fetch.

Pagination works with sorting and filtering.


List of available URL parameters
--------------------------------

- ``<prefix?><attribute name>``: filter by value(s)
- ``_since``: polling changes
- ``_sort``: order list
- ``_limit``: pagination max size
- ``_token``: pagination token


Combining all parameters
------------------------

Filtering, sorting and paginating can all be combined together.

* ``/articles?_sort=-last_modified&_limit=100``


POST /articles
==============

**Requires authentication**

Used to create a record on the server. The POST body is a JSON
mapping containing the values of the resource schema fields.

- ``url``
- ``title``
- ``added_by``

The POST response body is the newly created record, if all posted values are valid.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

**Optional values**

- ``added_on``
- ``excerpt``
- ``favorite``
- ``unread``
- ``status``
- ``is_article``
- ``resolved_url``
- ``resolved_title``

**Auto default values**

For v1, the server will assign default values to the following attributes:

- ``id``: *uuid*
- ``resolved_url``: ``url``
- ``resolved_title``: ``title``
- ``excerpt``: empty text
- ``status``: 0-OK
- ``favorite``: false
- ``unread``: true
- ``read_position``: 0
- ``is_article``: true
- ``last_modified``: current server timestamp
- ``stored_on``: current server timestamp
- ``marked_read_by``: null
- ``marked_read_on``: null
- ``word_count``: null

For v2, the server will fetch the content, and assign the following attributes with actual values:

- ``resolved_url``: the final URL obtained after all redirections resolved
- ``resolved_title``: The fetched page's title (content of <title>)
- ``excerpt``: The first 200 words of the article
- ``word_count``: Total word count of the article


Validation
----------

If the posted values are invalid (e.g. *field value is not an integer*)
an error response is returned with status ``400``.


:note:
    The ``status`` can take only ``0`` (OK) and ``1`` (archived), even though
    the server sets it to ``2`` when including deleted articles in the collection.


Conflicts
---------

Articles URL are unique per user (both ``url`` and ``resolved_url``).

:note:
    A ``url`` always resolves towards the same URL. If ``url`` is not unique, then
    its ``resolved_url`` won't either.

:note:
    Unicity on URLs is determined the full URL, including location hash.
    (e.g. http://news.com/day-1.html#paragraph1, http://spa.com/#/content/3)

:note:
    Deleted records are not taken into account for field unicity.

If the a conflict occurs, an error response is returned with status ``409``.
A ``existing`` attribute in the response gives the offending record.


DELETE /articles
================

**Requires authentication**

Delete multiple records. **Disabled by default**, see :ref:`configuration`.

The DELETE response is a JSON mapping with an ``items`` attribute, returning
the list of records that were deleted.

It supports the same filtering capabilities as GET.

If the request header ``If-Unmodified-Since`` is provided, and if the collection
has changed meanwhile, a ``412 Precondition failed`` error is returned.


GET /articles/<id>
==================

**Requires authentication**

Returns a specific record by its id.

For convenience and consistency, a header ``Last-Modified`` will also repeat the
value of ``last_modified``.

If the request header ``If-Modified-Since`` is provided, and if the record has not
changed meanwhile, a ``304 Not Modified`` is returned.


DELETE /articles/<id>
=====================

**Requires authentication**

Delete a specific record by its id.

The DELETE response is the record that was deleted.

If the record is missing (or already deleted), a ``404 Not Found`` is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    Once deleted, an article will appear in the collection with a deleted status
    (``status=2``) and will have most of its fields empty.


PATCH /articles/<id>
====================

**Requires authentication**

Modify a specific record by its id. The PATCH body is a JSON
mapping containing a subset of articles fields.

The PATCH response is the modified record (full).

**Modifiable fields**

- ``title``
- ``excerpt``
- ``favorite``
- ``unread``
- ``status``
- ``read_position``

Since article fields resolution is performed by the client in the first version
of the API, the following fields are also modifiable:

- ``is_article``
- ``resolved_url``
- ``resolved_title``

**Errors**

If a read-only field is modified, a ``400 Bad request`` error is returned.

If the record is missing (or already deleted), a ``404 Not Found`` error is returned. The client might
decide to ignore it.

If the request header ``If-Unmodified-Since`` is provided, and if the record has
changed meanwhile, a ``412 Precondition failed`` error is returned.

:note:
    ``last_modified`` is updated to the current server timestamp, only if a
    field value was changed.

:note:
    Changing ``read_position`` never generates conflicts.

:note:
    ``read_position`` is ignored if the value is lower than the current one.

:note:
    If ``unread`` is changed to false, ``marked_read_on`` and ``marked_read_by``
    are expected to be provided.

:note:
    If ``unread`` was already false, ``marked_read_on`` and ``marked_read_by``
    are not updated with provided values.

:note:
    If ``unread`` is changed to true, ``marked_read_by``, ``marked_read_on``
    and ``read_position`` are reset to their default value.

:note:
    As mentionned in the *Validation section*, an article status cannot take the value ``2``.


Conflicts
---------

If changing the article ``resolved_url`` violates the unicity constraint, a
``409 Conflict`` error response is returned (see :ref:`error channel <_error-responses>`).

:note:

    Note that ``url`` is a readonly field, and thus cannot generate conflicts
    here.
