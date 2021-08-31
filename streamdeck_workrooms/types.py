'''
Common types.
'''

from collections import namedtuple

# State of an action
ActionState = namedtuple('ActionStatus', ['status', 'error'], defaults=[None, None])