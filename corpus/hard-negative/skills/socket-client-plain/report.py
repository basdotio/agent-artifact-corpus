import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("metrics.example", 8125))
s.send(b"builds.completed:1|c\n")
s.close()
