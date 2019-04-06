#!/usr/bin/python3

import unittest
from unittest import mock
import socket
import stream
import subprocess

class TestPart2(unittest.TestCase):
    def test_get_init(self):
        with socket.socket() as sock:
            sock.connect(('picard.cs.colgate.edu', 80))
            mpd = mock.MagicMock
            mpd.initialization_url = mock.PropertyMock(
                    return_value='/dash/init_dash.mp4')
            with open('part2.mp4', 'wb') as out:
                stream.get_init(mpd, 'picard.cs.colgate.edu', sock, out)
            with open('part2.mp4', 'rb') as out:
                with subprocess.Popen(['curl', '-s',
                        'http://picard.cs.colgate.edu/dash/init_dash.mp4'],
                        stdout=subprocess.PIPE) as proc:
                    self.assertEqual(proc.stdout.read(), out.read()) 

if __name__ == '__main__':
    unittest.main()
