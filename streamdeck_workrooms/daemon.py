from argparse import Action, ArgumentParser, RawDescriptionHelpFormatter
import asyncio
import base64
import json
from logging import ERROR, basicConfig, debug, error, info
import mimetypes
from collections import namedtuple
import os
import os.path
import subprocess
import sys
import time
import traceback
import websockets


# Grace period before we show the user an error
ERROR_GRACE_PERIOD_SECONDS = 5


# User-facing error codes
EC_QUERY_SUBPROCESS_FAILED = 'E1'
EC_QUERY_DOM_FAILED = 'E2'


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
}


# Task to poll for state
async def state_poll(ws, on_images, off_images, unknown_images, none_images):
    MIC_INDEX = action_metadata['mic']['index']
    CAMERA_INDEX = action_metadata['camera']['index']
    HAND_INDEX = action_metadata['hand']['index']

    while True:
        await asyncio.sleep(1)

        now = time.time()
        status_array = [None] * len(action_metadata)
        errors_array = [None] * len(action_metadata)

        # Fill in the *_array values by querying browser
        try:
            out = subprocess.check_output(
                [os.path.join(os.path.curdir, 'query_browser_state.osa'), 'mic'],
                encoding='utf-8').strip()

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
                    status_array[CAMERA_INDEX] in ['ON', 'OFF']:
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

        except subprocess.CalledProcessError:
            error(traceback.format_exc())
            status_array = ['UNKNOWN'] * len(action_metadata)
            errors_array = [EC_QUERY_SUBPROCESS_FAILED] * len(action_metadata)

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

            debug('prev={}, current={}, next={}, new={}, next_time={}, now={}'.format(prev_state, current_state, next_state, new_state, next_time, now))

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
async def sd_listen(ws):
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
        if event == 'willAppear' or event == 'willDissappear':
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
                subprocess.check_call(
                    [os.path.join(os.path.curdir, 'toggle_browser_state.osa'), action],
                    encoding='utf-8')
            except subprocess.CalledProcessError:
                error(traceback.format_exc())


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

    # Load images that we need
    on_images = [
        load_image_string('state_mic_on.png'),
        load_image_string('state_camera_on.png'),
        load_image_string('state_hand_on.png'),
    ]
    off_images = [
        load_image_string('state_mic_off.png'),
        load_image_string('state_camera_off.png'),
        load_image_string('state_hand_off.png'),
    ]
    unknown_images = [
        load_image_string('state_mic_unknown.png'),
        load_image_string('state_camera_unknown.png'),
        load_image_string('state_hand_unknown.png'),
    ]
    none_images = [
        load_image_string('state_mic_none.png'),
        load_image_string('state_camera_none.png'),
        load_image_string('state_hand_none.png'),
    ]

    async with websockets.connect('ws://127.0.0.1:{}'.format(args.port)) as ws:
        info('established websocket connection')

        # Send the handshaking message back
        msg = json.dumps({'event': args.registerEvent, 'uuid': args.pluginUUID})
        await ws.send(msg)

        # Start up the event loop, one coroutine for each source
        done_tasks, pending_tasks = await asyncio.wait(
            [
                sd_listen(ws),
                state_poll(ws, on_images, off_images, unknown_images, none_images),
            ],
            return_when=asyncio.FIRST_EXCEPTION)

        # If one of the tasks exited due to an exception, just re-raise it to
        # terminate everything and get the stack trace written to stderr
        for dt in done_tasks:
            if dt.exception() is not None:
                raise dt.exception()

        info('event loop exited')

if __name__ == '__main__':
    asyncio.run(main())