# haku bot

这是原 [py-hakuBot](https://github.com/weilinfox/py-hakuBot) 的重构，但并没有达到它的完善程度

日志 flask

message 消息 alarm 定时消息 misc 杂项消息

配置文件使用 yaml 和 json

数据库使用 sqlite3

消息发送 api 支持 [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)

故障上报到指定 qq 或群组

不重启 bot 即可更新插件

配合 systemd 实现更新后的自动重启

黑白名单（qq/群组过滤），先判断黑名单，后判断白名单

### 项目结构

+ haku
  + core.py
  + report.py
  + config.py
  + plugin.py
  + cache.py
  + frontend.py
+ api
  + gocqhttp.py
+ data
  + sqlite.py
  + json.py
  + log.py
+ handlers
  + message.py
  + alarm.py
  + misc.py
+ plugins
  + commands
    + some_plugins.py
+ main.py

### 目录结构

+ files
  + sqlite
    + some.db
  + json
    + some.json
  + log
    + some.txt
  + config.yaml
+ libs
  + go-cqhttp
    + go-cqhttp
    + device.json
