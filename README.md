# haku bot

はく研究所

在 Linux 配合 [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) 使用的 qq bot 。

这是原 [py-hakuBot](https://github.com/weilinfox/py-hakuBot) 的重构，但并没有达到它的完善程度。

以及，架构依然乱糟糟。

## 特性

+ 日志 flask
+ message 消息 alarm 定时消息 misc 杂项消息
+ 配合 POSIX Alarm Signal 实现的定时消息和定时任务
+ 配置文件使用 yaml 和 json
+ 数据库使用 sqlite3
+ 消息发送 api 支持 go-cqhttp
+ 故障上报到指定 qq 或群组
+ 不重启 bot 即可实现配合 git 的插件更新
+ 配合 systemd 实现更新整个 bot 后的自动重启
+ 黑名单（qq/群组消息过滤）
+ 每个插件独立的黑白名单（qq/群组过滤），先判断黑名单，后判断白名单

## 插件

+ [archlinux](plugins/commands/archlinux.py) Archlinux 包查询
+ [debian](plugins/commands/debian.py) Debian 包查询
+ [ubuntu](plugins/commands/ubuntu.py) Ubuntu 包查询
+ [loongnix](plugins/commands/loongnix.py) Loongnix20 for Loongarch64 包查询
+ [music](plugins/commands/music.py) 网易云音乐
+ [qqmusic](plugins/commands/qqmusic.py) QQ音乐（似乎不能用了）
+ [forecast](plugins/commands/forecast.py) 和风天气
+ [yiyan](plugins/commands/yiyan.py) 一言
+ [rss](plugins/commands/rss.py) rss 订阅
+ [loongnews](plugins/commands/loongnews.py) 龙芯官网新闻订阅
+ [dizzylab](plugins/commands/dizzylab.py) dizzylab 搜索
+ [qqweight](plugins/commands/qqweight.py) QQ 号权重查询
+ [schedules](plugins/commands/schedules.py) 定时消息
+ [commands](plugins/commands/commands.py) 定时命令
+ [update](plugins/commands/update.py) 更新 bot

## 项目结构

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

## 缓存和配置目录结构

+ files
  + sqlite
    + some.db
  + json
    + some.json
  + log
    + some.txt
  + config.yaml
  + keys.yaml
