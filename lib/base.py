import os

def check_directories():
    if not os.path.exists("echo"):
        os.mkdir("echo")
    if not os.path.exists("msg"):
        os.mkdir("msg")
    if not os.path.exists("out"):
        os.mkdir("out")
