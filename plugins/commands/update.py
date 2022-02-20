"""
重载插件
TODO: git pull
"""
import data.log
import handlers.message


def run(message) -> str:
    data.log.get_logger().debug('Update plugin cache')
    try:
        plugin = handlers.message.Plugin()
        plugin.reload()
    except Exception as e:
        return f'Update plugin cache failed: {e}'
    return 'Update plugin cache success'


def bye():
    data.log.get_logger().debug('run ping.quit()')
