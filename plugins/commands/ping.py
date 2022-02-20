"""
ping
TODO: ping ip
"""
import data.log


def config():
    data.log.get_logger().debug('run ping.config()')


def run(message) -> str:
    data.log.get_logger().debug('run ping.run(message)')
    return 'pong!'


def bye():
    data.log.get_logger().debug('run ping.quit()')
