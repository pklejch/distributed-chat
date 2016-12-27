import click
from .server import Server
from .client import Client

@click.group()
def interface():
    pass


@interface.command()
def gui():
    raise Exception


@interface.command()
@click.argument("ip_port")
@click.argument("ip_port_next")
def cli(ip_port, ip_port_next):
    ip, port = ip_port.split(":")
    ip_next, port_next = ip_port_next.split(":")
    server = Server(0, ip, int(port))
    client = Client(0, ip_next, int(port_next))

    server.start()
    client.start()






def main():
    interface()