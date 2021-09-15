'''
Communicate with the browser.
'''


from .types import ActionState

import asyncio
import json
from logging import error, info
import os.path
from random import randint
import time
import traceback


# Grace period before we show the user an error
ERROR_GRACE_PERIOD_SECONDS = 5


# User-facing error codes
EC_QUERY_SUBPROCESS_FAILED_STATUS = 'E1'
EC_QUERY_DOM_FAILED = 'E2'
EC_CHROME_APPLESCRIPT_DISABLED = 'E3'
EC_QUERY_SUBPROCESS_FAILED_EXCEPTION = 'E4'


async def listen(ws, analytics_collect, action_metadata, on_images, off_images, unknown_images, none_images):
    '''
    Coroutine to listen to state changes from the browser.
    '''

    MIC_INDEX = action_metadata['mic']['index']
    CAMERA_INDEX = action_metadata['camera']['index']
    HAND_INDEX = action_metadata['hand']['index']
    CALL_INDEX = action_metadata['call']['index']

    while True:
        await asyncio.sleep(1)

        now = time.time()
        status_array = [None] * len(action_metadata)
        errors_array = [None] * len(action_metadata)

        # Fill in the *_array values by querying browser
        #
        # Error handling here is quite involved, as there are many different
        # layers in which things could fail. Some of these errors mean that we
        # can't interpret any results (e.g. failed to execute the query script),
        # while some are partial (e.g. we can't find the "hand" button).
        try:
            proc = await asyncio.create_subprocess_exec(
                os.path.join(os.path.curdir, 'query_browser_state.osa'),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            out, err = await proc.communicate()
            out = out.decode('utf-8').strip()
            err = err.decode('utf-8').strip()

            if proc.returncode == 0:
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
                        status_array[CAMERA_INDEX] in ['ON', 'OFF'] and \
                        status_array[CALL_INDEX] in ['ON', 'OFF']:
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
            else:
                error('query failed with status {}\nstdout={}\nstderr={}'.format(proc.returncode, out, err))

                # Compute the error code, defaulting to something generic
                ec = EC_QUERY_SUBPROCESS_FAILED_STATUS
                if 'Executing JavaScript through AppleScript is turned off' in err:
                    ec = EC_CHROME_APPLESCRIPT_DISABLED

                status_array = ['UNKNOWN'] * len(action_metadata)
                errors_array = [ec] * len(action_metadata)

        except Exception:
            error(traceback.format_exc())
            status_array = ['UNKNOWN'] * len(action_metadata)
            errors_array = [EC_QUERY_SUBPROCESS_FAILED_EXCEPTION] * len(action_metadata)

        # Report query timing, sampled at 1%
        if randint(0, 100) == 0:
            await analytics_collect(
                t='timing',
                utc='query',
                utv='subprocess',
                utt=int((time.time() - now) * 1000))

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

                # If we've transitioned to a "good" state and the user has
                # pressed a button to initate this change, track and report the
                # time from press to state change.
                if current_state.status in ['ON', 'OFF'] and \
                        data['action_time'] is not None:
                    latency = now - data['action_time']
                    await analytics_collect(
                        t='timing',
                        utc='toggle',
                        utv=name,
                        utt=int(latency * 1000))

                # No matter what, any attempt by the user to toggle the state is
                # now stale; reset it
                data['action_time'] = None

                msg = {'event': 'setImage', 'context': context, 'payload': {}}
                if current_state.status == 'OFF':
                    msg['payload']['image'] = off_images[index]
                elif current_state.status == 'ON':
                    msg['payload']['image'] = on_images[index]
                else:
                    msg['payload']['image'] = none_images[index]

                    if current_state.status not in ['NONE', 'UNKNOWN']:
                        error(f'Unexpected status {current_state.status}')
                        await analytics_collect(
                            t='exception',
                            exd=f'{name.title()}UnexpectedState{current_state.status}',
                            exf=0)

                await ws.send(json.dumps(msg))

            # Update the error if necessary
            if prev_state.error != current_state.error:
                info('{} error changed from {} to {}'.format(name, prev_state.error, current_state.error))

                if current_state.error is not None:
                    await analytics_collect(
                        t='exception', exd=f'{name.title()}Error{current_state.error}', exf=0)

                await ws.send(
                    json.dumps({
                        'event': 'setTitle',
                        'context': context,
                        'payload': {'title': current_state.error}}))