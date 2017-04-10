# coding=utf-8

from xcat3.image.os import base


class RedhatImage(base.Image):
    def __init__(self, path, install_dir, name):
        super(RedhatImage, self).__init__(path, install_dir, name)

    def parse_info(self):
        return

    def copycd(self, disk_info):
        pass
