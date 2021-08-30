'''
Analytics implementation.

This is implemented using the Google Analytics Measuremnt Protocol (Universal
Analytics). 
'''

from aiohttp import ClientSession
from logging import debug, error, info
import traceback
from urllib.parse import urlencode

# TODO: Maybe use the 'qt' paramter to track queue time.
async def listen(queue, enabled, tid, cid, user_agent=None):
    '''
    Listen for analytics events by polling `queue` and using `client_session` to
    send them to the Google Analytics backend.

    See
    https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters
    for desriptions of the required `tid` and `cid` arguments.
    '''

    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent

    async with ClientSession(headers=headers if headers else None) as cs:
        while True:
            params = await queue.get()

            info(f'{"not " if not enabled else ""}sending analytics {params}')

            if not enabled:
                continue

            # Update parameters with the rest of what is required
            params.update({
                'v': 1,
                'tid': tid,
                'cid': cid,
            })

            data = urlencode(params).encode('utf-8')
            url = 'https://www.google-analytics.com/collect'

            try:
                await cs.post(url, data=data)
            except Exception:
                error(traceback.format_exc())


async def collect(queue, t, **kwargs):
    '''
    Collect analytics and enqueue them for sending.

    See
    https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters
    for information on the types of hits (specified by `t`) that can be posted
    as well parameters required for each type.
    '''

    params = { 't': t }
    params.update(kwargs)

    await queue.put(params)