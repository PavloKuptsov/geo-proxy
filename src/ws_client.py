import threading

import websocket

WEB_UI_WS_URL = 'ws://127.0.0.1:8080/_push'
# WEB_UI_WS_URL = 'ws://100.96.1.2:8080/_push'
RESTART_ATTEMPTS = 5


class ClientSocket:
    def __init__(self, url):
        self.ws = websocket.WebSocketApp(url, on_close=self.on_close)
        self.restarts = 0
        self.ws.run_forever()

    def on_close(self, ws, close_status_code, close_msg):
        if self.restarts <= RESTART_ATTEMPTS:
            print('Connection closed, reinstating')
            self.restarts += 1
            self.ws.run_forever()
        else:
            print('Connection closed, restart attempts exceeded')


def run():
    return ClientSocket(WEB_UI_WS_URL)


def run_in_thread():
    thread = threading.Thread(target=run, args=())
    thread.daemon = True
    thread.start()


if __name__ == '__main__':
    print('Starting WS client')
    ClientSocket(WEB_UI_WS_URL)
