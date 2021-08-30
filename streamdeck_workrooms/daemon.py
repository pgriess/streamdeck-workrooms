from aiohttp import ClientSession
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import asyncio
import base64
from hashlib import blake2b
import json
from logging import ERROR, basicConfig, debug, error, info
import math
import mimetypes
from collections import namedtuple
import os
import os.path
from functools import partial
from random import Random, randint
import subprocess
import sys
import time
import traceback
from urllib.parse import urlencode
from uuid import UUID
import websockets


# Grace period before we show the user an error
ERROR_GRACE_PERIOD_SECONDS = 5


# User-facing error codes
EC_QUERY_SUBPROCESS_FAILED = 'E1'
EC_QUERY_DOM_FAILED = 'E2'
EC_CHROME_APPLESCRIPT_DISABLED = 'E3'


# State of an action
ActionState = namedtuple('ActionStatus', ['status', 'error'], defaults=[None, None])


# Global state for each action
action_metadata = {
    'mic': {
        'index': 0,
        'context': None,
        'current': ActionState(),
        'next': ActionState(),
        'next_time': 0,
    },
    'camera': {
        'index': 1,
        'context': None,
        'current': ActionState(),
        'next': ActionState(),
        'next_time': 0,
    },
    'hand': {
        'index': 2,
        'context': None,
        'current': ActionState(),
        'next': ActionState(),
        'next_time': 0,
    },
    'call': {
        'index': 3,
        'context': None,
        'current': ActionState(),
        'next': ActionState(),
        'next_time': 0,
    },
}


# Task to get state updates from the browser
async def browser_listen(ws, analytics, on_images, off_images, unknown_images, none_images):
    MIC_INDEX = action_metadata['mic']['index']
    CAMERA_INDEX = action_metadata['camera']['index']
    HAND_INDEX = action_metadata['hand']['index']
    CALL_INDEX = action_metadata['call']['index']

    while True:
        await asyncio.sleep(1)

        now = time.time()
        status_array = [None] * len(action_metadata)
        errors_array = [None] * len(action_metadata)

        # Fill in the *_array values by querying browser
        #
        # Error handling here is quite involved, as there are many different
        # layers in which things could fail. Some of these errors mean that we
        # can't interpret any results (e.g. failed to execute the query script),
        # while some are partial (e.g. we can't find the "hand" button).
        try:
            proc = await asyncio.create_subprocess_exec(
                os.path.join(os.path.curdir, 'query_browser_state.osa'),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            out, err = await proc.communicate()
            out = out.decode('utf-8').strip()
            err = err.decode('utf-8').strip()

            if proc.returncode == 0:
                # The 'NONE' sentinel value means no rooms were found. Expand that
                # to fill each of the actions rather than doing that in query.js
                if out == 'NONE':
                    status_array = ['NONE'] * len(action_metadata)
                else:
                    status_array = out.split(' ')

                assert len(status_array) == len(action_metadata)

                # Some calls don't have a hand status, which will cause it to
                # come back from the query as UNKNOWN. In this case, don't show
                # the user the confusing UNKNOWN icon. Just consider it NONE
                # since this is expected.
                if status_array[HAND_INDEX] == 'UNKNOWN' and \
                        status_array[MIC_INDEX] in ['ON', 'OFF'] and \
                        status_array[CAMERA_INDEX] in ['ON', 'OFF'] and \
                        status_array[CALL_INDEX] in ['ON', 'OFF']:
                    status_array[HAND_INDEX] = 'NONE'

                # Any entries in the status_array that are UNKNOWN mean
                # that we couldn't find the DOM node. Mark this as an error in
                # the relevant field.
                #
                # XXX: This isn't really true as we could have found the node but
                #      not been able to interpret its contents. Update query.js to
                #      differentiate the different failure modes.
                for index, status in enumerate(status_array):
                    if status != 'UNKNOWN':
                        continue

                    errors_array[index] = EC_QUERY_DOM_FAILED
            else:
                error('query failed with status {}\nstdout={}\nstderr={}'.format(proc.returncode, out, err))

                # Compute the error code, defaulting to the generic
                # EC_QUERY_SUBPROCESS_FAILED
                ec = EC_QUERY_SUBPROCESS_FAILED
                if 'Executing JavaScript through AppleScript is turned off' in err:
                    ec = EC_CHROME_APPLESCRIPT_DISABLED

                status_array = ['UNKNOWN'] * len(action_metadata)
                errors_array = [ec] * len(action_metadata)

        except Exception:
            error(traceback.format_exc())
            status_array = ['UNKNOWN'] * len(action_metadata)
            errors_array = [EC_QUERY_SUBPROCESS_FAILED] * len(action_metadata)

        # Report query timing, sampled at 1%
        if randint(0, 100) == 0:
            await analytics(
                t='timing',
                utc='query',
                utv='subprocess',
                utt=int((time.time() - now) * 1000))

        assert len(status_array) == len(action_metadata)
        assert len(errors_array) == len(action_metadata)

        # Loop over all actions and update the Stream Deck accordingly
        for name, data in action_metadata.items():
            index = data['index']
            context = data['context']
            prev_state = data['current']
            current_state = data['current']
            next_state = data['next']
            next_time = data['next_time']

            new_state = ActionState(status_array[index], errors_array[index])

            # We have no context; don't update
            if context is None:
                continue

            # Update the next state if it's changed
            if new_state != next_state:
                data['next'] = next_state = new_state
                data['next_time'] = next_time = now

            # Nothing has changed, no more work to do
            if next_state == current_state:
                continue

            # All changes are flushed after ERROR_GRACE_PERIOD_SECONDS
            if now > (next_time + ERROR_GRACE_PERIOD_SECONDS):
                data['current'] = current_state = next_state

            # Changes to a "good" status cause the entire next state to be
            # propagated immediately since we want to be in an error state for
            # as short a time as possible.
            if next_state.status != current_state.status and next_state.status != 'UNKNOWN':
                data['current'] = current_state = next_state

            # Update the status if necessary
            if prev_state.status != current_state.status:
                info('{} status changed from {} to {}'.format(name, prev_state.status, current_state.status))

                msg = {'event': 'setImage', 'context': context, 'payload': {}}
                if current_state.status == 'OFF':
                    msg['payload']['image'] = off_images[index]
                elif current_state.status == 'ON':
                    msg['payload']['image'] = on_images[index]
                elif current_state.status in ['NONE', 'UNKNOWN']:
                    msg['payload']['image'] = none_images[index]
                else:
                    raise Exception('Unexpected status {}'.format(current_state.status))

                await ws.send(json.dumps(msg))

            # Update the error if necessary
            if prev_state.error != current_state.error:
                info('{} error changed from {} to {}'.format(name, prev_state.error, current_state.error))

                await ws.send(
                    json.dumps({
                        'event': 'setTitle',
                        'context': context,
                        'payload': {'title': current_state.error}}))


# Task to listen to Stream Deck commands
async def streamdeck_listen(ws, analytics):
    global context_mic

    while True:
        msg = json.loads(await ws.recv())

        event = msg.get('event')
        now = time.time()

        # I'm not sure why this could happen, but all messages that we currently
        # handle require it, so just check up-front
        if 'action' not in msg:
            continue

        action = msg['action'].split('.')[-1]
        data = action_metadata[action]

        # XXX: This assumes that we only have one action of a given type
        #      active at once. I don't think that is actually the case.
        if event == 'willAppear' or event == 'willDisappear':
            context = msg['context']

            if event == 'willAppear':
                action_metadata[action]['context'] = context
            else:
                action_metadata[action]['context'] = None
                action_metadata[action]['current'] = ActionState()
                action_metadata[action]['next'] = ActionState()
                action_metadata[action]['next_time'] = now

            continue

        if event == 'keyUp':
            state = data['current']

            # We have no idea what the current state is; do nothing
            if state.status is None:
                continue

            # We have an error; direct the user to the help page for this error
            if state.error is not None:
                info('opening up the help page for error {}'.format(state.error))
                await ws.send(json.dumps({
                    'event': 'openUrl',
                    'context': context,
                    'payload': {
                        'url': 'https://github.com/pgriess/streamdeck-workrooms/wiki/Errors#{}'.format(state.error.lower())
                    }
                }))

                continue

            # We have an unexpected status; direct the user to the help page for this status
            if state.status in ['NONE', 'UNKNOWN']:
                info('opening up the help page')
                await ws.send(json.dumps({
                    'event': 'openUrl',
                    'context': context,
                    'payload': {
                        'url': 'https://github.com/pgriess/streamdeck-workrooms/wiki/Help'
                    }
                }))

                continue

            info('toggling {} status'.format(action))
            try:
                proc = await asyncio.create_subprocess_exec(
                    os.path.join(os.path.curdir, 'toggle_browser_state.osa'),
                    action,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)

                out, err = await proc.communicate()
                out = out.decode('utf-8').strip()
                err = err.decode('utf-8').strip()

                if proc.returncode != 0:
                    error('toggle failed with status {}\nstdout={}\nstderr={}'.format(
                        proc.returncode,
                        out,
                        err))

            except Exception:
                error(traceback.format_exc())

            await analytics(t='event', ec='Actions', ea=action.title())


# Task to listen for analytics events and send them
#
# TODO: Maybe use the 'qt' paramter to track queue time.
async def analytics_listen(queue, client_session, tid, cid):
    while True:
        params = await queue.get()

        # Update parameters with the rest of what is required
        params.update({
            'v': 1,
            'tid': tid,
            'cid': cid,
        })

        data = urlencode(params).encode('utf-8')
        url = 'https://www.google-analytics.com/collect'

        try:
            await client_session.post(url, data=data)
            info(f'analytics {params} sent')
        except Exception:
            error(traceback.format_exc())


# Send analytics
async def analytics_send(queue, t, **kwargs):
    params = { 't': t }
    params.update(kwargs)
    debug(f'enqueueing analytics {params}')

    await queue.put(params)


# Get the plugin version string from manifest.json
def get_plugin_version():
    with open('manifest.json', encoding='utf-8') as f:
        jo = json.load(f)
        return jo['Version']


# Get a stable client UUID based on the serial number of the connected Stream
# Deck device
def get_client_uuid():
    out = subprocess.check_output(
        ('system_profiler', 'SPUSBDataType'),
        stderr=subprocess.DEVNULL)

    # TODO: Harden parsing here to handle the case where the device does not have a
    #       serial number. I'm not sure this could happen, but if it does we'd want
    #       to make sure that we fail rather than grab whatever the next serial
    #       number happens to be (especially if the next one is 0 which is common).
    found_device = False
    for l in out.decode('utf-8').split('\n'):
        l = l.strip()

        if not found_device:
            if 'Stream Deck' in l:
                found_device = True

            continue

        if not l.startswith('Serial Number: '):
            continue

        serial = l.split(' ')[2]

        h = blake2b(
            serial.encode('utf-8'), digest_size=16, salt='workrooms'.encode('utf-8'))
        u = UUID(bytes=h.digest())

        return str(u)

    raise Exception('Failed to find serial number')


def load_image_string(asset_name):
    '''
    Return a string-ified representation of the given asset, suitable for
    passing to SD via setImage command.
    '''

    fp = os.path.join(os.path.curdir, asset_name)
    mt, _ = mimetypes.guess_type(fp)
    assert mt is not None

    with open(fp, 'rb') as f:
        content = base64.b64encode(f.read()).decode()
        return 'data:{};base64,{}'.format(mt, content)


async def main():
    ap = ArgumentParser(
        description='''
Command handler for an Elgato Stream Deck plugin for Facebook actions.
''',
        formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument(
		'-v', action='count', default=0,
		help='increase logging verbosity; can be used multiple times')

    # Options defined by the Stream Deck plugin prototol
    ap.add_argument('-port')
    ap.add_argument('-pluginUUID')
    ap.add_argument('-registerEvent')
    ap.add_argument('-info')

    args = ap.parse_args()

    basicConfig(
        style='{', format='{asctime} {message}', level=ERROR - args.v * 10,
        stream=sys.stderr)

    plugin_version = get_plugin_version()
    client_id = get_client_uuid()
    info(f'Facebook Workplace version {plugin_version} starting with client ID {client_id}')

    # Load images that we need
    on_images = [
        load_image_string('state_mic_on.png'),
        load_image_string('state_camera_on.png'),
        load_image_string('state_hand_on.png'),
        load_image_string('state_call_on.png'),
    ]
    off_images = [
        load_image_string('state_mic_off.png'),
        load_image_string('state_camera_off.png'),
        load_image_string('state_hand_off.png'),
        load_image_string('state_call_off.png'),
    ]
    unknown_images = [
        load_image_string('state_mic_unknown.png'),
        load_image_string('state_camera_unknown.png'),
        load_image_string('state_hand_unknown.png'),
        load_image_string('state_call_unknown.png'),
    ]
    none_images = [
        load_image_string('state_mic_none.png'),
        load_image_string('state_camera_none.png'),
        load_image_string('state_hand_none.png'),
        load_image_string('state_call_none.png'),
    ]

    user_agent = f'StreamDeckWorkroomsBot/{plugin_version}'

    async with websockets.connect('ws://127.0.0.1:{}'.format(args.port)) as ws, \
            ClientSession(headers={'User-Agent': user_agent}) as cs:
        info('established websocket connection')

        # Send the handshaking message back
        msg = json.dumps({'event': args.registerEvent, 'uuid': args.pluginUUID})
        await ws.send(msg)

        async_tasks = []

        # Set up analytics
        #
        # Tasks interact with the analytics system by getting a callback that
        # they can use to publich metrics. If analytics has been enabled, set up
        # this callback and any associated infrastructure. If not, provide a
        # stub that does not send anything.
        #
        # TODO: Enable analytics based on the global settings which the user can
        #       interact with via the Property Inspector
        if client_id == 'cdd89ecb-0c73-b56b-c1a1-19eb15646443':
            analytics_queue = asyncio.Queue()
            async_tasks += [analytics_listen(analytics_queue, cs, 'UA-18586119-5', client_id)]

            # Wrap analytics_send() in a partial so that we don't leak global
            # state into the callers or require them to pass the same
            # boilerplate parameters repeatedly
            analytics = partial(
                analytics_send, analytics_queue,
                an='StreamDeckWorkrooms', av=plugin_version, aip=1, npa=1)
        else:
            async def analytics_stub(**kwargs):
                info(f'not sending analytics {kwargs}')

            analytics = analytics_stub

        async_tasks += [streamdeck_listen(ws, analytics)]
        async_tasks += [browser_listen(ws, analytics, on_images, off_images, unknown_images, none_images)]

        await analytics(t='event', ec='System', ea='Launch')

        done_tasks, pending_tasks = await asyncio.wait(
            async_tasks,
            return_when=asyncio.FIRST_EXCEPTION)

        # If one of the tasks exited due to an exception, just re-raise it to
        # terminate everything and get the stack trace written to stderr
        for dt in done_tasks:
            if dt.exception() is not None:
                raise dt.exception()

        info('event loop exited')

if __name__ == '__main__':
    asyncio.run(main())
