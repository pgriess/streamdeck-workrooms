'''
Communicate with Stream Deck.

See https://developer.elgato.com/documentation/stream-deck/sdk.
'''

from .types import ActionState

import asyncio
import base64
import json
from logging import error, info
import mimetypes
import os.path
import time
import traceback

async def process_message(msg, now, ws, analytics_collect, action_metadata):
    '''
    Process a single Stream Deck message.
    '''

    # Some global messages like 'deviceDidConnect' don't have an action. At this
    # point, we don't care about any of them so just ignore
    if 'action' not in msg:
        return

    event = msg.get('event')
    action = msg['action'].split('.')[-1]
    data = action_metadata[action]

    # This messages signifies that an instance of the given action is going to
    # appear on the screen. Stash away its context so that we can use it
    # communicate with the Stream Deck later.
    #
    # XXX: This assumes that we only have one action of a given type
    #      active at once. I don't think that is actually the case.
    if event == 'willAppear':
        data['context'] = msg['context']
        return

    # This message signifies that an instance of the given action is going to be
    # removed from the screen. Clear out our metadata so that things will
    # initialize correctly the next time we get a willAppear message.
    #
    # XXX: As with 'willAppear', this assumes that there is a single instance of
    #      this action.
    if event == 'willDisappear':
        data['context'] = None
        data['current'] = ActionState()
        data['next'] = ActionState()
        data['next_time'] = now
        data['action_time'] = None
        return

    if event == 'keyUp':
        context = data['context']
        state = data['current']

        # We have no idea what the current state is; do nothing
        if state.status is None:
            return

        # We haven't been appeared, so we have no context; do nothing
        if context is None:
            return

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

            return

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

            return

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
                await analytics_collect(t='exception', exd='ToggleError', exf=0)
            else:
                data['action_time'] = now

        except Exception:
            error(traceback.format_exc())
            await analytics_collect(t='exception', exd='ToggleException', exf=0)

        if analytics_collect:
            await analytics_collect(t='event', ec='Actions', ea=action.title())


async def listen(ws, analytics_collect, action_metadata):
    '''
    Coroutine to listen for Stream Deck commands.
    '''

    # Process live messages from Stream Deck
    while True:
        msg = json.loads(await ws.recv())
        now = time.time()
        await process_message(msg, now, ws, analytics_collect, action_metadata)


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