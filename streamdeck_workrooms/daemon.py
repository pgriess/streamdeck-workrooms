from argparse import ArgumentParser, RawDescriptionHelpFormatter
import asyncio
import base64
import json
from logging import ERROR, basicConfig, error, info
import mimetypes
import os
import os.path
import subprocess
import sys
import traceback
import websockets

action_metadata = {
    'mic': {
        'index': 0,
        'context': None,
        'state': None,
    },
    'camera': {
        'index': 1,
        'context': None,
        'state': None,
    },
    'hand': {
        'index': 2,
        'context': None,
        'state': None,
    },
}

# Task to poll for Workrooms state
async def state_poll(ws, on_images, off_images, unknown_images, none_images):
    MIC_INDEX = action_metadata['mic']['index']
    CAMERA_INDEX = action_metadata['camera']['index']
    HAND_INDEX = action_metadata['hand']['index']

    while True:
        await asyncio.sleep(1)

        out = None
        try:
            out = subprocess.check_output(
                [os.path.join(os.path.curdir, 'query_browser_state.osa'), 'mic'],
                encoding='utf-8').strip()
        except subprocess.CalledProcessError:
            error(traceback.format_exc())
            out = 'NONE NONE NONE'

        next_states_array = out.split(' ')

        # Some calls don't have a hand state, which will cause it to come back
        # from the query as UNKNOWN. In this case, don't show the user the
        # confusing "unknown" icon. Just consider it "none" since this is
        # expected.
        if next_states_array[HAND_INDEX] == 'UNKNOWN' and \
                next_states_array[MIC_INDEX] in ['ON', 'OFF'] and \
                next_states_array[CAMERA_INDEX] in ['ON', 'OFF']:
            next_states_array[HAND_INDEX] = 'NONE'

        for name, data in action_metadata.items():
            index = data['index']
            context = data['context']
            current_state = data['state']
            next_state = next_states_array[index]

            # Nothing has changed; don't update
            if current_state == next_state:
                continue

            # We have no context; don't update
            if context is None:
                continue

            info('{} state changed from {} to {}'.format(name, current_state, next_state))

            msg = {'event': 'setImage', 'context': context, 'payload': {}}
            if next_state == 'OFF':
                msg['payload']['image'] = off_images[index]
            elif next_state == 'ON':
                msg['payload']['image'] = on_images[index]
            elif next_state == 'NONE':
                msg['payload']['image'] = none_images[index]
            else:
                msg['payload']['image'] = unknown_images[index]

            await ws.send(json.dumps(msg))

            data['state'] = next_state


# Task to listen to Stream Deck commands
async def sd_listen(ws):
    global context_mic

    while True:
        msg = json.loads(await ws.recv())
        event = msg.get('event')

        # I'm not sure why this could happen, but all messages that we currently
        # handle require it, so just check up-front
        if 'action' not in msg:
            continue

        action = msg['action'].split('.')[-1]

        # XXX: This assumes that we only have one action of a given type
        #      active at once. I don't think that is actually the case.
        if event == 'willAppear' or event == 'willDissappear':
            context = msg['context']

            if event == 'willAppear':
                action_metadata[action]['context'] = context
            else:
                action_metadata[action]['context'] = None
                action_metadata[action]['state'] = None

            continue

        if event == 'keyUp':
            # We have no idea what the current state is; do nothing
            if action_metadata[action]['state'] == None:
                continue

            if action_metadata[action]['state'] in ['NONE', 'UNKNOWN']:
                info('opening up the help page')
                await ws.send(json.dumps({
                    'event': 'openUrl',
                    'context': context,
                    'payload': {
                        'url': 'https://github.com/pgriess/streamdeck-workrooms/wiki/Help'
                    }
                }))

                continue

            info('toggling {} state'.format(action))
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