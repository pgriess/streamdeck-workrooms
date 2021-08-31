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


async def listen(ws, analytics_collect, action_metadata):
    '''
    Coroutine to listen for Stream Deck commands.
    '''

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

            await analytics_collect(t='event', ec='Actions', ea=action.title())


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