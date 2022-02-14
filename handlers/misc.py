
class Misc:
    """
    杂项类
    """
    def __init__(self, misc_type: str, sub_type: str, user_id: int):
        self.misc_type = misc_type
        self.sub_type = sub_type
        self.user_id = user_id
        self.group_id = 0
        self.time = 0
        self.info: dict

    def handle(self):
        pass
