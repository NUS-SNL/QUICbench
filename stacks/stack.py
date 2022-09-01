from abc import ABC, abstractmethod

class Stack(ABC):
    """
    An interface for a Stack in our experiments.
    A stack can run a server instance on a remote machine and connect to it via a local client
    to generate a flow for that stack.
    """

    @abstractmethod
    def run_remote_server(self, port_no, cc_algo, duration_s):
        pass

    def run_remote_server_wlogs(self, port_no, cc_algo, duration_s, log_path):
        pass

    @abstractmethod
    def run_client(self, port_no, cc_algo, duration_s):
        pass

    @staticmethod
    @abstractmethod
    def get_cc_algos():
        pass
