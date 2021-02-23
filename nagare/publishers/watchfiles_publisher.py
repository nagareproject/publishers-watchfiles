# --
# Copyright (c) 2008-2021 Net-ng.
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

    def generate_banner(self):
        banner = super(Publisher, self).generate_banner()
        directory = self.plugin_config['directory'] + ('/**' if self.plugin_config['recursive'] else '')
        return banner + ' on events from directory `{}`'.format(directory)

    def _serve(self, app, directory, create, recursive, **config):
        super(Publisher, self)._serve(app)

        if not os.path.exists(directory) and create:
            os.mkdir(directory)

        config = {k: v for k, v in config.items() if k not in publisher.Publisher.CONFIG_SPEC}

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

        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()

        observer.join()
