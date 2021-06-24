from argparse import ArgumentParser, RawDescriptionHelpFormatter
import asyncio
import base64
import json
from logging import WARNING, basicConfig, info
import mimetypes
import os
import os.path
import subprocess
import sys
import websockets

context_mic = None


# Task to poll for Workrooms state
async def state_poll(ws, off_image, on_image, unknown_image):
    current_state = None

    while True:
        await asyncio.sleep(1)

        # Nothing to do if we don't have an active context
        if context_mic is None:
            continue

        out = subprocess.check_output(
            [os.path.join(os.path.curdir, 'query_browser_state.osa'), 'mic'],
            encoding='utf-8').strip()

        if out == current_state:
            continue

        info('current state changed from {} to {}'.format(current_state, out))
        current_state = out

        msg = {'event': 'setImage', 'context': context_mic, 'payload': {}}
        if current_state == 'OFF':
            msg['payload']['image'] = off_image
        elif current_state == 'ON':
            msg['payload']['image'] = on_image
        else:
            msg['payload']['image'] = unknown_image

        await ws.send(json.dumps(msg))


# Task to listen to Stream Deck commands
async def sd_listen(ws):
    global context_mic

    while True:
        msg = json.loads(await ws.recv())
        event = msg.get('event')

        if event == 'willAppear':
            action = msg['action']
            if action == 'in.std.streamdeck.workrooms.mic':
                context_mic = msg['context']

        if event == 'willDissappear':
            action = msg['action']
            if action == 'in.std.streamdeck.workrooms.mic':
                context_mic = None

        if event == 'keyUp':
            info('toggling mute state')
            subprocess.check_call(
                [os.path.join(os.path.curdir, 'toggle_browser_state.osa'), 'mic'],
                encoding='utf-8')


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
        style='{', format='{asctime} {message}', level=WARNING - args.v * 10,
        stream=sys.stderr)

    # Load images that we need
    off_image = load_image_string('state_mic_off.png')
    on_image = load_image_string('state_mic_on.png')
    unknown_image = load_image_string('state_mic_unknown.png')

    async with websockets.connect('ws://127.0.0.1:{}'.format(args.port)) as ws:
        info('established websocket connection')

        # Send the handshaking message back
        msg = json.dumps({'event': args.registerEvent, 'uuid': args.pluginUUID})
        await ws.send(msg)

        # Listen for events from Stream Deck
        await asyncio.wait(
            [
                sd_listen(ws),
                state_poll(ws, off_image, on_image, unknown_image),
            ],
            return_when=asyncio.FIRST_EXCEPTION)

if __name__ == '__main__':
    asyncio.run(main())