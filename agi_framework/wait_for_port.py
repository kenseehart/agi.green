import socket
import time

def wait_for_port(host, port, timeout=120.0):
    """Wait until a port starts accepting TCP connections.
    Args:
    port (int): Port number
    host (str): Host address on which the port should exist
    timeout (float): In seconds. How long to wait before raising errors.
    """
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as ex:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError('Waited too long for the port {} on host {} to start accepting '
                                   'connections.'.format(port, host)) from ex

print("Waiting for port 5678...")
wait_for_port('localhost', 5678)
print("Port 5678 is open")
