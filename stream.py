#!/usr/bin/python3

from argparse import ArgumentParser
import logging
import mympd
import myhttp
import socket
import sys

logging.basicConfig(stream=sys.stderr,level=logging.DEBUG,format='%(message)s')

def issue_request(sock, request):
    logging.debug(request)

    msg_utf = request.deparse().encode()
    sock.send(msg_utf)

    raw_response = b''
    bufsize = 4096
    new_data = sock.recv(bufsize)
    while b"\r\n" not in new_data:
        raw_response += new_data
        new_data = sock.recv(bufsize)
    raw_response += new_data

    # Parse response header
    end_header = raw_response.index(b'\r\n\r\n') + 4
    raw_header = raw_response[:end_header]
    logging.debug(raw_header)
    response = myhttp.HTTPResponse.parse(raw_header.decode())
    logging.debug(response)

    # Receive response body
    content_length = response.get_header('Content-Length')
    if content_length is not None:
        content_length = int(content_length)
        raw_body = raw_response[end_header:]
        while (len(raw_body) < content_length):
            raw_recv = sock.recv(4096)
            if not raw_recv:
                break
            raw_body += raw_recv
    else:
        raw_body = None

    return response, raw_body

def get_mpd(hostname, url, sock):

    req = myhttp.HTTPRequest("GET", myhttp.URI(url), headers={'Host':hostname})
    (response, raw_body) = issue_request(sock, req)

    mpdfile = mympd.MPDFile(raw_body)

    return mpdfile

def get_init(mpd, hostname, sock, out):
    req = myhttp.HTTPRequest("GET", myhttp.URI(mpd.initialization_url), headers={'Host':hostname})
    (response, raw_body) = issue_request(sock, req)
    out.write(raw_body)

    return

def get_segments(mpd, hostname, sock, out):
    representations = mpd.representations

    for r in range(len(representations)):
        num_segments = 4
        rep = representations[r]
        for segment in range(num_segments):
            byte_range = rep.segment_range(r*num_segments + segment)
            req = myhttp.HTTPRequest("GET", myhttp.URI(rep.base_url), headers={'Host':hostname, 'Range': 'bytes='+str(byte_range[0])+'-'+str(byte_range[1])})
            (response, raw_body) = issue_request(sock, req)
            out.write(raw_body)
    return

def stream(hostname, url, out):
    sock = socket.socket()
    sock.connect((hostname, 80))

    # Perform streaming
    mpd = get_mpd(hostname, url, sock)
    get_init(mpd, hostname, sock, out)
    get_segments(mpd, hostname, sock, out)

    sock.close()

    return

def main():
    # Parse arguments
    arg_parser = ArgumentParser(description='DASH client', add_help=False)
    arg_parser.add_argument('-u', '--url', dest='url', action='store',
            default='http://picard.cs.colgate.edu/dash/manifest.mpd',
            help='URL for MPD file')
    arg_parser.add_argument('-o', '--output', dest='output', action='store',
            default='test.mp4',
            help='Name of file in which to store video data')
    settings = arg_parser.parse_args()

    uri = myhttp.URI(settings.url)
    if settings.output is None:
        sink = sys.stdout
    else:
        sink = open(settings.output, 'wb')

    stream(uri.host, uri.abs_path, sink)

    if settings.output is not None:
        sink.close()

if __name__ == '__main__':
    main()
