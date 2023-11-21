import websocket

WEB_UI_WS_URL = 'ws://127.0.0.1:8080/_push'


class ClientSocket:
    def __init__(self, url):
        self.ws = websocket.WebSocketApp(url, on_close=self.on_close)
        self.ws.run_forever()

    def on_close(self, ws, close_status_code, close_msg):
        print('Connection closed, reinstating')
        self.ws.run_forever()


if __name__ == '__main__':
    print('Starting WS client')
    ClientSocket(WEB_UI_WS_URL)
