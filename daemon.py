from streamdeck_workrooms import analytics
from streamdeck_workrooms import browser
from streamdeck_workrooms import streamdeck
from streamdeck_workrooms.types import ActionState

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import asyncio
from collections import defaultdict
import json
from logging import ERROR, basicConfig, info
from functools import partial
import sys
from uuid import uuid4
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
    info(f'Facebook Workplace version {plugin_version} starting')

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
        await ws.send(
            json.dumps({'event': args.registerEvent, 'uuid': args.pluginUUID}))

        # Get global plugin settings
        #
        # This requires a round-trip to Stream Deck -- we send a
        # getGlobalSettings message and then get back didReceiveGlobalSettings.
        # Doing this during startup is a bit tricky since Stream Deck is going
        # to send us some other messages as part of the process of bringing
        # things up, e.g. deviceDidConnect and willAppear, etc. Ignore anythig
        # other than the global settings. In the future, maybe we'll care about
        # these other messages which will require a re-structuring here.
        await ws.send(
            json.dumps({'event': 'getGlobalSettings', 'context': args.pluginUUID}))

        settings = {}
        while not settings:
            msg = json.loads(await ws.recv())
            if msg['event'] != 'didReceiveGlobalSettings':
                continue

            settings = msg['payload']['settings']

            # We didn't have any settings, create and store them
            if not settings:
                settings = {'client_id': str(uuid4())}
                await ws.send(
                    json.dumps({
                        'event': 'setGlobalSettings',
                        'context': args.pluginUUID,
                        'payload': settings}))

        async_tasks = []

        # Set up analytics
        #
        # Tasks interact with the analytics system by getting a callback that
        # they can use to publich metrics. Set up this callback and any
        # associated infrastructure.
        analytics_queue = asyncio.Queue()
        async_tasks += [
            analytics.listen(
                analytics_queue, True, 'UA-18586119-5', settings['client_id'],
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
