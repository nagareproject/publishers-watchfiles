# --
# Copyright (c) 2008-2024 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import os
import time
from functools import partial

from watchdog import events
from watchdog.observers import api

from nagare.server import publisher, reference


class Publisher(publisher.Publisher):
    """Watch a directory for files modifications events."""

    OBSERVERS = {
        'auto': 'watchdog.observers:Observer',
        'inotify': 'watchdog.observers.inotify:InotifyObserver',
        'fsevents': 'watchdog.observers.fsevents:FSEventsObserver',
        'kqueue': 'watchdog.observers.kqueue:KqueueObserver',
        'winapi': 'watchdog.observers.read_directory_changes:WindowsApiObserver',
        'polling': 'watchdog.observers.polling:PollingObserver',
    }

    CONFIG_SPEC = dict(
        publisher.Publisher.CONFIG_SPEC,
        observer='string(default="auto")',
        timeout='integer(default={})'.format(api.DEFAULT_OBSERVER_TIMEOUT),
        directory='string(help="directory to watch")',
        recursive='boolean(default=False, help="watch the whole directories tree starting at ``directory``")',
        patterns='list(default=None, help="files patterns to watch")',
        ignore_patterns='list(default=None, help="files patterns to ignore")',
        ignore_directories='boolean(default=False, help="ignore directories modifications events")',
        case_sensitive='boolean(default=True, help="match/ignore patterns are case sensitive")',
        create='boolean(default=True, help="create ``directory`` if it doesn\'t exist")',
    )

    def __init__(self, name, dist, services_service, observer, timeout, **config):
        services_service(super(Publisher, self).__init__, name, dist, observer=observer, timeout=timeout, **config)
        self.observer = reference.load_object(observer if ':' in observer else self.OBSERVERS[observer])[0](timeout)

    def generate_banner(self):
        """Generate the banner to display on start.

        Returns:
            the banner
        """
        banner = super(Publisher, self).generate_banner()
        directory = self.plugin_config['directory'] + ('/**' if self.plugin_config['recursive'] else '')
        return banner + ' on events from directory `{}`'.format(directory)

    def handle_event(self, app, services, event):
        # Keywords passed to the application:
        #  - ``event_type``: type of the event (``moved``, ``deleted``, ``created``, ``modified`` or ``closed``)
        #  - ``src_path``: path of the modified file/directory
        #  - ``is_directory``: ``True`` if the event was emitted for a directory
        #  - ``dest_path``: in case of ``moved`` event, the new file/directory path
        try:
            self.start_handle_request(
                app,
                services,
                event_type=event.event_type,
                src_path=event.src_path,
                is_directory=event.is_directory,
                dest_path=getattr(event, 'dest_path', None),
            )
        except Exception:  # noqa: S110
            pass

    def _serve(
        self,
        app,
        directory,
        create,
        recursive,
        patterns,
        ignore_patterns,
        ignore_directories,
        case_sensitive,
        services_service,
        **config,
    ):
        """Start the publisher.

        Args:
            app (nagare.server.base_application): the application to receive the files modifications events
            directory (str): directory to watch
            create (boolean): create ```directory`` if it doesn't exist
            recursive (boolean): watch the whole directory tree starting at ``directory``

        Returns:
            str: the banner
        """
        super(Publisher, self)._serve(app)

        if not os.path.exists(directory) and create:
            os.mkdir(directory)

        # Keep only the configuration options specifics to this publisher
        config = {k: v for k, v in config.items() if k not in publisher.Publisher.CONFIG_SPEC}

        event_handler = events.PatternMatchingEventHandler(
            patterns, ignore_patterns, ignore_directories, case_sensitive
        )
        event_handler.on_any_event = partial(self.handle_event, app, services_service)

        self.observer.schedule(event_handler, directory, recursive=recursive)
        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()

        self.observer.join()
