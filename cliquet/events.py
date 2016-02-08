from collections import OrderedDict

import transaction
from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPException

from cliquet.logs import logger
from cliquet.utils import strip_uri_prefix, Enum


ACTIONS = Enum(CREATE='create',
               DELETE='delete',
               READ='read',
               UPDATE='update')


class _ResourceEvent(object):
    def __init__(self, action, timestamp, request):
        self.request = request
        resource_name = request.current_resource_name

        self.payload = {'timestamp': timestamp,
                        'action': action,
                        'uri': strip_uri_prefix(request.path),
                        'user_id': request.prefixed_userid,
                        'resource_name': resource_name}

        matchdict = dict(request.matchdict)

        if 'id' in request.matchdict:
            matchdict[resource_name + '_id'] = matchdict.pop('id')

        self.payload.update(**matchdict)


class ResourceRead(_ResourceEvent):
    """Triggered when a resource is read.
    """
    def __init__(self, action, timestamp, read_records, request):
        super(ResourceRead, self).__init__(action, timestamp, request)
        self.read_records = read_records


class ResourceChanged(_ResourceEvent):
    """Triggered when a resource is changed.
    """
    def __init__(self, action, timestamp, impacted_records, request):
        super(ResourceChanged, self).__init__(action, timestamp, request)
        self.impacted_records = impacted_records


def setup_transaction_hook(config):
    """
    Resource events are plugged with the transactions of ``pyramid_tm``.

    When a transaction is committed, events are sent.
    On rollback nothing happens.
    """
    def _notify_resource_events(current, request):
        """Notify the accumulated resource events if transaction succeeds.
        """
        for event in request.get_resource_events():
            try:
                request.registry.notify(event)
            except HTTPException as e:
                current.doom()  # too late!
                raise e
            except Exception:
                logger.error("Unable to notify", exc_info=True)

    def on_new_request(event):
        """When a new request comes in, hook on transaction commit.
        """
        # Since there is one transaction per batch, ignore subrequests.
        if hasattr(event.request, 'parent'):
            return
        current = transaction.get()
        current.addBeforeCommitHook(_notify_resource_events,
                                    args=(current, event.request,))

    config.add_subscriber(on_new_request, NewRequest)


def get_resource_events(request):
    """
    Request helper to return the list of events triggered on resources.
    The list is sorted chronologically (see OrderedDict)
    """
    events = request.bound_data.get("resource_events")
    if events is None:
        return []
    return events.values()


def notify_resource_event(request, timestamp, data, action, old=None):
    """
    Request helper to stack a resource event.

    If a similar event (same resource, same action) already occured during the
    current transaction (e.g. batch) then just extend the impacted records of
    the previous one.
    """
    if action == ACTIONS.READ:
        if not isinstance(data, list):
            data = [data]
        impacted = data
    elif action == ACTIONS.CREATE:
        impacted = [{'new': data}]
    elif action == ACTIONS.DELETE:
        if not isinstance(data, list):
            data = [data]
        impacted = [{'old': r} for r in data]
    elif action == ACTIONS.UPDATE:
        impacted = [{'new': data, 'old': old}]

    # Get previously triggered events.
    events = request.bound_data.setdefault("resource_events", OrderedDict())
    resource_name = request.current_resource_name

    # Add to impacted records or create new event.
    group_by = resource_name + action
    if group_by in events:
        if action == ACTIONS.READ:
            events[group_by].read_records.extend(impacted)
        else:
            events[group_by].impacted_records.extend(impacted)
    else:
        if action == ACTIONS.READ:
            event_cls = ResourceRead
        else:
            event_cls = ResourceChanged
        event = event_cls(action, timestamp, impacted, request)
        events[group_by] = event
