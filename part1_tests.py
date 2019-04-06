#!/usr/bin/python3

import stream
import unittest
import socket
import myhttp
import mympd

class TestPart1(unittest.TestCase):
    def test_issue_request(self):
        with socket.socket() as sock:
            sock.connect(('picard.cs.colgate.edu', 80))
            request = myhttp.HTTPRequest('GET', '/test.txt', 
                    headers={'Host' : 'picard.cs.colgate.edu'}) 
            response, body = stream.issue_request(sock, request)
            self.assertIsInstance(response, myhttp.HTTPResponse)
            self.assertIsInstance(body, bytes)
            self.assertEqual(response.status_code, 200) 
            self.assertEqual(body, b'This is a test.\nThis is only a test.\n') 

    def test_get_mpd(self):
        with socket.socket() as sock:
            sock.connect(('picard.cs.colgate.edu', 80))
            mpd = stream.get_mpd('picard.cs.colgate.edu', '/dash/manifest.mpd',
                    sock)
            self.assertIsInstance(mpd, mympd.MPDFile)
            self.assertEqual(mpd.initialization_url, '/dash/init_dash.mp4')
            self.assertEqual(len(mpd.representations), 6)

if __name__ == '__main__':
    unittest.main()
