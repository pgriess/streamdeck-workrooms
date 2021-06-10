from argparse import ArgumentParser, RawDescriptionHelpFormatter
from logging import ERROR, basicConfig, info
import sys

def main():
    ap = ArgumentParser(
        description='''
Command handler for an Elgato Stream Deck plugin for Facebook actions.
''',
        formatter_class=RawDescriptionHelpFormatter)
    ap.add_argument(
		'-v', action='count', default=0,
		help='increase logging verbosity; can be used multiple times')

    # TODO: Need to actually use these
    ap.add_argument('-port')
    ap.add_argument('-pluginUUID')
    ap.add_argument('-registerEvent')
    ap.add_argument('-info')

    args = ap.parse_args()
    basicConfig(
        style='{', format='{message}', level=ERROR - args.v * 10,
        stream=sys.stderr)

    info('port={}, plugin={}, event={}, info={}'.format(
        args.port, args.pluginUUID, args.registerEvent, args.info))
