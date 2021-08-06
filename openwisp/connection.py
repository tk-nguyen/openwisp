"""Track all the connections that openwrt returns in conntrack

"""


class Connection:
    # We will track each connection per source with their bytes tranferred
    conns = dict()

    def __init__(self, src):
        self.src = src

    def add_conn(self, dst, port, bytes):
        self.conns[(dst, port)] = bytes
