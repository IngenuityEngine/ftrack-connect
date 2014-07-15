# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import logging
import os
import json
import base64
import sys
import subprocess
import collections

import ftrack


class LaunchApplicationHook(object):
    '''LaunchApplicationHook class.'''

    def __init__(self):
        self.logger = logging.getLogger(
            'ftrack.hook.' + self.__class__.__name__
        )

    def __call__(self, event, applicationIdentifier, context, **data):
        '''Default launch-application hook.

        The hook callback accepts *event*, the *applicationIdentifier* and the
        application *context*.

        '''
        command = self._getApplicationLaunchCommand(applicationIdentifier)

        data['context'] = context
        data['applicationIdentifier'] = applicationIdentifier
        environment = self._getApplicationEnvironment(
            data
        )

        success = True
        message = '{0} application started.'.format(applicationIdentifier)

        # Environment must contain only strings.
        self._conformEnvironment(environment)

        try:
            options = dict(
                env=environment,
                close_fds=True
            )

            if sys.platform == 'win32':
                # Ensure subprocess is detached so closing connect will not also
                # close launched applications.
                options['creationflags'] = subprocess.CREATE_NEW_CONSOLE
            else:
                options['preexec_fn'] = os.setsid

            process = subprocess.Popen(command, **options)

        except (OSError, TypeError):
            self.logger.exception(
                '{0} application could not be started with command "{1}".'.format(
                    applicationIdentifier, command
                )
            )
            success = False
            message = '{0} application could not be started.'.format(
                applicationIdentifier
            )

        else:
            message += ' (pid={0})'.format(process.pid)

        return {
            'success': success,
            'message': message
        }

    def _conformEnvironment(self, mapping):
        '''Ensure all entries in *mapping* are strings.

        .. note::

            The *mapping* is modified in place.

        '''
        if not isinstance(mapping, collections.MutableMapping):
            return

        for key, value in mapping.items():
            if isinstance(value, collections.Mapping):
                self._conformEnvironment(value)
            else:
                value = str(value)

            del mapping[key]
            mapping[str(key)] = value

    def _getApplicationLaunchCommand(self, applicationIdentifier):
        '''Return application command based on OS and *applicationIdentifier*.
        '''
        command = None

        if applicationIdentifier == 'hieroplayer':

            if sys.platform == 'win32':
                # HieroPlayer application command when running Windows.
                command = ['hieroplayer.exe']

            elif sys.platform == 'darwin':
                # HieroPlayer application command when running OSX.
                command = [
                    'open',
                    '/Applications/HieroPlayer1.8v1/HieroPlayer1.8v1.app'
                ]

            else:
                # HieroPlayer application command when running something else.
                pass

        return command

    def _getApplicationEnvironment(self, eventData=None):
        '''Return list of environment variables based on *context*.

        The list will also contain the variables available in the current
        session.

        '''
        # Copy appropitate environment variables to new environment.
        environment = {}

        environment.setdefault(
            'FTRACK_SERVER', os.environ.get('FTRACK_SERVER')
        )
        environment.setdefault(
            'FTRACK_APIKEY', os.environ.get('FTRACK_APIKEY')
        )
        environment.setdefault(
            'LOGNAME', os.environ.get('LOGNAME')
        )

        environment.setdefault(
            'FTRACK_LOCATION_PLUGIN_PATH',
            os.environ.get('FTRACK_LOCATION_PLUGIN_PATH')
        )

        environment.setdefault(
            'PYTHONPATH', os.path.dirname(ftrack.__file__)
        )

        # Add ftrack connect event to environment.
        if eventData is not None:
            try:
                applicationContext = base64.b64encode(
                    json.dumps(
                        eventData
                    )
                )
            except:
                self.logger.exception(
                    'Context could not be converted correctly. {0}'.format(context)
                )
            else:
                environment['FTRACK_CONNECT_EVENT'] = applicationContext

        self.logger.debug('Setting new environment to {0}'.format(environment))

        return environment


def register(registry, **kw):
    '''Register hook.'''
    ftrack.TOPICS.subscribe(
        'ftrack.launch-application',
        LaunchApplicationHook(),
        callbackID='ftrack-connect-default-hook'
    )
