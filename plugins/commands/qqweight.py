"""
QQ 号权重查询
"""
import requests

from handlers.message import Message


def run(message: Message) -> str:
    req = list(message.raw_message.split(' ', 1))
    try:
        id = message.user_id
        if len(req) > 1:
            id = int(req[1])
    except Exception:
        help_msg = "QQ权重查询，越高越好"
        if len(req) > 1 and req[1].strip() == "help":
            return help_msg
        return "不合法的参数: " + req[1]
    else:
        try:
            resp = requests.get(url="http://tc.tfkapi.top/API/qqqz.php?type=json&qq="+str(id), timeout=15)
            if resp.status_code != 200:
                return "Get 请求返回错误码 "+str(resp.status_code) + ", 出错的 ID: " + str(id)
            content = resp.json()
            code = content.get("code")
            msg = content.get("msg")
            qz = content.get("qz")
            if code == 200:
                return f"查询成功 ID: {id}\n查询状态: {msg}\n权重: {qz}"
            else:
                return f"查询异常 ID: {id}\n查询状态: {msg}\n权重: {qz}"
        except Exception as e:
            return "查询请求出错，出错的 ID: " + str(id) + "\n错误信息: " + str(e)


if __name__ == "__main__":
    print(run(Message(user_id=123456, message_type="", sub_type="", message_id=0)))
