from argparse import ArgumentParser, RawDescriptionHelpFormatter
import asyncio
import base64
import json
from logging import FileHandler, INFO, basicConfig, error, getLogger, info, warn
from logging.handlers import SysLogHandler
import mimetypes
import os
import os.path
import subprocess
import sys
import traceback
import websockets


async def hello(event, uuid, ws_url, muted_image, active_image):
    async with websockets.connect(ws_url) as ws:
        info('established websocket connection')
        out_msg = json.dumps({'event': event, 'uuid': uuid})
        info('sending: {}'.format(out_msg))
        await ws.send(out_msg)

        current_state = None
        context = None
        retry_counter = 0

        while True:
            try:
                in_msg = await asyncio.wait_for(ws.recv(), 1)
                info('received: {}'.format(in_msg))

                in_jo = json.loads(in_msg)

                # Track the current context value
                if 'context' in in_jo:
                    if context is None:
                        context = in_jo['context']
                        info('setting context to {}'.format(context))

                    if context != in_jo['context']:
                        error('context changed from {} to {}'.format(context, in_jo['context']))
                        context = in_jo['context']

                if in_jo.get('event') == 'keyUp':
                    info('toggling mute state')
                    subprocess.check_call('/Users/pgriess/src/pgriess-streamdeck-fb/toggle_mute_state.osa', encoding='utf-8')

            except asyncio.TimeoutError:
                out = subprocess.check_output('/Users/pgriess/src/pgriess-streamdeck-fb/query_mute_state.osa', encoding='utf-8').strip()
                info('current state is {}'.format(out))
                retry_counter += 1

                if out != current_state or (retry_counter % 5) == 0:
                    info('current state changed from {} to {}'.format(current_state, out))
                    current_state = out

                    out_jo = {'event': 'setImage', 'context': context, 'payload': {}}
                    if current_state == 'ACTIVE':
                        out_jo['payload']['image'] = active_image
                    elif current_state == 'MUTED':
                        out_jo['payload']['image'] = muted_image
                    else:
                        # XXX XXX XXX XXX
                        out_jo['payload']['image'] = active_image

                    out_msg = json.dumps(out_jo)
                    info('sending: {}'.format(out_msg))
                    await ws.send(out_msg)
            except websockets.exceptions.ConnectionClosedOK:
                info('ws server disconnected; exiting')
                return
            except:
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


def main():
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
        style='{', format='{asctime} {message}', level=INFO - args.v * 10,
        stream=sys.stderr)

    if not os.isatty(sys.stdout.fileno()):
        getLogger().addHandler(FileHandler('/Users/pgriess/.streamdeck.log'))

    ws_url = 'ws://127.0.0.1:{}'.format(args.port)
    info('connecting to {}'.format(ws_url))

    # Load images that we need
    muted_image = load_image_string('muted.png')
    active_image = load_image_string('active.png')

    asyncio.get_event_loop().run_until_complete(
        hello(args.registerEvent, args.pluginUUID, ws_url, muted_image, active_image))
