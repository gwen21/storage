# -*- coding: utf-8 -*-

from os import environ
import asyncio
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

class MyComponent(ApplicationSession):

    async def onJoin(self, details):

        def on_event(event_type=None, key=None):
            print("Got event {} on file : {}".format(event_type, key))

        await self.subscribe(on_event, u'v1.storage.event')

if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("AUTOBAHN_DEMO_ROUTER", u"ws://crossbar:8080/ws"),
        u"realm1",
    )
    runner.run(MyComponent)
