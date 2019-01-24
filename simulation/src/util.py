import simpy


class Network:
    TRANSMISSION_DELAY = 0.1

    def __init__(self, env):
        self.env = env
        self.peers = {}
        self.next_address = 0

    def register(self, peer):
        # TODO Reuse addresses.
        address = self.next_address
        self.next_address += 1
        self.peers[address] = peer
        return address

    def send(self, sender_id, sender_address, recipient_address,
             event_factory):
        """
        Send a message by scheduling an event.
        :param event_factory: A function taking a sender ID and a recipient
            (*not* a recipient address) and returning a simPy event to be
            scheduled with an appropriate delay.
        """
        delay = 0
        if sender_address != recipient_address:
            delay += Network.TRANSMISSION_DELAY
        recipient = self.peers.get(recipient_address)
        if recipient is None:
            raise UnassignedAddressError
        self.env.schedule(event_factory(sender_id, recipient), delay=delay)

    def send_query(self, sender_id, sender_address, recipient_address,
                   queried_id, in_event_id):
        self.send(sender_id, sender_address, recipient_address,
                  lambda si, r: SendQuery(self.env, si, r, queried_id,
                                          in_event_id))

    def send_response(self, sender_id, sender_address, recipient_address,
                      queried_ids, queried_peer_info, in_event_id):
        self.send(sender_id, sender_address, recipient_address,
                  lambda si, r: SendResponse(self.env, si, r, queried_ids,
                                             queried_peer_info, in_event_id))


class SendQuery(simpy.events.Event):
    def __init__(self, env, sender_id, recipient, queried_id, in_event_id):
        super().__init__(env)
        self.ok = True
        self.sender_id = sender_id
        self.recipient = recipient
        self.queried_id = queried_id
        self.in_event_id = in_event_id
        self.callbacks.append(SendQuery.action)

    def action(self):
        self.recipient.recv_query(self.sender_id, self.queried_id,
                                  self.in_event_id)


class SendResponse(simpy.events.Event):
    def __init__(self, env, sender_id, recipient, queried_ids,
                 queried_peer_info, in_event_id):
        super().__init__(env)
        self.ok = True
        self.sender_id = sender_id
        self.recipient = recipient
        self.queried_ids = queried_ids
        self.queried_peer_info = queried_peer_info
        self.in_event_id = in_event_id
        self.callbacks.append(SendResponse.action)

    def action(self):
        self.recipient.recv_response(self.sender_id, self.queried_ids,
                                     self.queried_peer_info, self.in_event_id)


class UnassignedAddressError(Exception):
    pass


def bit_overlap(a, b):
    """Calculate the number of bits at the start that are the same."""
    m = min(len(a), len(b))
    return len(next((a[:m] ^ b[:m]).split('0b1', count=1)))


def do_delayed(env, delay, function, *args):
    """
    Do something with a delay.

    Creates a process that calls function with args after delay.
    """
    def gen():
        yield env.timeout(delay)
        function(*args)
    env.process(gen())


def format_ids(queried_id, queried_ids):
    """Pretty-print an ID and set of prefixes."""
    s = str(queried_id)
    if len(queried_ids) > 1:
        s += ' ({' + ', '.join((str(qid) for qid in queried_ids)) + '})'
    return s
