from streamdeck_workrooms import analytics
from streamdeck_workrooms import browser
from streamdeck_workrooms import streamdeck
from streamdeck_workrooms.types import ActionState

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import asyncio
from collections import defaultdict
from hashlib import blake2b
import json
from logging import ERROR, basicConfig, info
import os.path
from functools import partial
import subprocess
import sys
from uuid import UUID
import websockets


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


async def main_async():
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
    images = defaultdict(list)
    for state in ['ON', 'OFF', 'UNKNOWN', 'NONE']:
        for action in ['mic', 'camera', 'hand', 'call']:
            images[state] += [
                streamdeck.load_image_string(
                    f'state_{action}_{state.lower()}.png')]

    async with websockets.connect('ws://127.0.0.1:{}'.format(args.port)) as ws:
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
        analytics_enabled = client_id == 'cdd89ecb-0c73-b56b-c1a1-19eb15646443'
        analytics_queue = asyncio.Queue()
        async_tasks += [
            analytics.listen(
                analytics_queue, analytics_enabled, 'UA-18586119-5', client_id,
                user_agent=f'StreamDeckWorkroomsBot/{plugin_version}')]
        analytics_collect = partial(
            analytics.collect, analytics_queue,
            an='StreamDeckWorkrooms', av=plugin_version, aip=1, npa=1)

        async_tasks += [streamdeck.listen(ws, analytics_collect, action_metadata)]
        async_tasks += [
            browser.listen(
                ws, analytics_collect, action_metadata,
                images['ON'], images['OFF'], images['UNKNOWN'], images['NONE'])]

        await analytics_collect(t='event', ec='System', ea='Launch')

        done_tasks, pending_tasks = await asyncio.wait(
            async_tasks,
            return_when=asyncio.FIRST_EXCEPTION)

        # If one of the tasks exited due to an exception, just re-raise it to
        # terminate everything and get the stack trace written to stderr
        for dt in done_tasks:
            if dt.exception() is not None:
                raise dt.exception()

        info('event loop exited')


def main():
    asyncio.run(main_async())


if __name__ == '__main__':
    main()
