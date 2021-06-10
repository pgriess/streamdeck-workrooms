from argparse import ArgumentParser, RawDescriptionHelpFormatter
import asyncio
import json
from logging import FileHandler, INFO, basicConfig, error, getLogger, info, warn
from logging.handlers import SysLogHandler
import os
import subprocess
import sys
import traceback
import websockets


async def hello(event, uuid, ws_url):
    async with websockets.connect(ws_url) as ws:
        info('established websocket connection')
        out_msg = json.dumps({'event': event, 'uuid': uuid})
        info('sending: {}'.format(out_msg))
        await ws.send(out_msg)

        current_state = None
        context = None

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

            except asyncio.TimeoutError:
                out = subprocess.check_output('/Users/pgriess/src/pgriess-streamdeck-fb/query_mute_state.osa', encoding='utf-8').strip()
                info('current state is {}'.format(out))

                if out != current_state:
                    info('current state changed from {} to {}'.format(current_state, out))

                current_state = out

                out_jo = {'event': 'setState', 'context': context, 'payload': {}}
                if current_state == 'ACTIVE':
                    out_jo['payload']['state'] = 0
                elif current_state == 'MUTED':
                    out_jo['payload']['state'] = 1
                else:
                    pass

                out_msg = json.dumps(out_jo)
                info('sending: {}'.format(out_msg))
                await ws.send(out_msg)
            except:
                error(traceback.format_exc())


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

    asyncio.get_event_loop().run_until_complete(
        hello(args.registerEvent, args.pluginUUID, ws_url))
