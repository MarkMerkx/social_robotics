from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from alpha_mini_rug import show_camera_stream
from autobahn.twisted.util import sleep


@inlineCallbacks
def behavior(session):
    yield session.subscribe(show_camera_stream, "rom.sensor.sight.stream")
    yield session.call("rom.sensor.sight.stream")

    pass


def main(session, details):
    behavior(session)
    pass


wamp = Component(
    transports=[
        {
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["json"],
            "max_retries": 0,
        }
    ],
    realm="rie.67cff07599b259cf43b04548",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
