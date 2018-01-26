# --
# Copyright (c) 2008-2018 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import time
from watchdog import observers, events

from nagare.server import publishers


class Publisher(publishers.Publisher):

    CONFIG_SPEC = {
        'directory': 'string',
        'recursive': 'boolean(default=False)',
        'patterns': 'list(default=None)', 'ignore_patterns': 'list(default=None)',
        'ignore_directories': 'boolean(default=False)',
        'case_sensitive': 'boolean(default=True)'
    }

    def _serve(self, app, directory, recursive, **config):
        event_handler = events.PatternMatchingEventHandler(**config)
        event_handler.on_any_event = lambda event: app(
            event_type=event.event_type,
            src_path=event.src_path,
            is_directory=event.is_directory,
            dest_path=getattr(event, 'dest_path', None)
        )

        observer = observers.Observer()
        observer.schedule(event_handler, directory, recursive=recursive)

        print time.strftime('%x %X -', time.localtime()), observer.__class__.__name__, 'watching', directory

        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()

        observer.join()
