# haku bot

日志 flask
message 消息
alarm 定时消息
misc 杂项消息
配置文件
数据库
消息发送 api
故障上报
go-cqhttp 管理

reload：
不重启 重载插件
重启 重启程序

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
