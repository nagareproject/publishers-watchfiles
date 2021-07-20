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
    """Watch a directory for files modifications events"""

    CONFIG_SPEC = dict(
        publisher.Publisher.CONFIG_SPEC,
        directory='string(help="directory to watch")',
        recursive='boolean(default=False, help="watch the whole directories tree starting at ``directory``")',
        patterns='list(default=None, help="files patterns to watch")',
        ignore_patterns='list(default=None, help="files patterns to ignore")',
        ignore_directories='boolean(default=False, help="ignore directories modifications events")',
        case_sensitive='boolean(default=True, help="match/ignore patterns are case sensitive")',
        create='boolean(default=True, help="create ``directory`` if it doesn\'t exist")'
    )

    def generate_banner(self):
        """Generate the banner to display on start

        Returns:
            the banner
        """
        banner = super(Publisher, self).generate_banner()
        directory = self.plugin_config['directory'] + ('/**' if self.plugin_config['recursive'] else '')
        return banner + ' on events from directory `{}`'.format(directory)

    def _serve(self, app, directory, create, recursive, services_service, **config):
        """Start the publisher

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

        event_handler = events.PatternMatchingEventHandler(**config)

        # Keywords passed to the application:
        #  - ``event_type``: type of the event (``moved``, ``deleted``, ``created``, ``modified`` or ``closed``)
        #  - ``src_path``: path of the modified file/directory
        #  - ``is_directory``: ``True`` if the event was emitted for a directory
        #  - ``dest_path``: in case of ``moved`` event, the new file/directory path
        event_handler.on_any_event = lambda event: self.start_handle_request(
            app,
            services_service,
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
