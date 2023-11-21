import websocket


class ClientSocket:
    def __init__(self, url):
        self.opened = False
        self.ws = websocket.WebSocketApp(url,
                                         on_close=self.on_close)
        self.ws.run_forever()

    def on_close(self, ws, close_status_code, close_msg):
        self.ws.run_forever()
