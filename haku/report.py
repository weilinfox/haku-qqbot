
from typing import List

admin_group: List[int] = []
admin_user: List[int] = []


def report_set_admin_group(group_id: int):
    global admin_group
    admin_group.append(group_id)


def report_set_admin_user(user_id: int):
    global admin_user
    admin_user.append(user_id)


def report_send(message: str):
    for id in admin_group:
        # TODO: send_group_message()
        pass
    for id in admin_user:
        # TODO: send_private_message()
        pass
