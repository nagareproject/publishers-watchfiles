# --
# Copyright (c) 2008-2019 Net-ng.
# All rights reserved.
#
# This software is licensed under the BSD License, as described in
# the file LICENSE.txt, which you should have received as part of
# this distribution.
# --

import os
import time
from watchdog import observers, events

from nagare.server import publisher


class Publisher(publisher.Publisher):

    CONFIG_SPEC = dict(
        publisher.Publisher.CONFIG_SPEC,
        directory='string',
        recursive='boolean(default=False)',
        patterns='list(default=None)',
        ignore_patterns='list(default=None)',
        ignore_directories='boolean(default=False)',
        case_sensitive='boolean(default=True)',
        create='boolean(default=True)'
    )

    def _serve(self, app, directory, create, recursive, **config):
        if not os.path.exists(directory) and create:
            os.mkdir(directory)

        event_handler = events.PatternMatchingEventHandler(**config)
        event_handler.on_any_event = lambda event: self.start_handle_request(
            app,
            event_type=event.event_type,
            src_path=event.src_path,
            is_directory=event.is_directory,
            dest_path=getattr(event, 'dest_path', None)
        )

        observer = observers.Observer()
        observer.schedule(event_handler, directory, recursive=recursive)

        print('%s %s - watching %s' % (time.strftime('%x %X', time.localtime()), observer.__class__.__name__, directory))

        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()

        observer.join()
