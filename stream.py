#!/usr/bin/python3

from argparse import ArgumentParser
import logging
import mympd
import myhttp
import socket
import sys
import threading

logging.basicConfig(stream=sys.stderr,level=logging.DEBUG,format='%(message)s')

to_play_buffer = []
played_segments=[]

#Variables for getting frames
curr_representation =
curr_frame_displayed_num =
curr_segment_num =

prev_bitrate=


#Variables for deciding when frames are fetched
join_segment =
buffer_capacity =
max_current_buffer =
bytes_in_buffer =
segments_in_buffer =
bandwidth =
played_segment_bytes =

#Variables for playback
curr_playback_frame =
fps = 30  #This should be determined by

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
    print(raw_body)

    return
def update_variables():
    ''' Update the global variables before we call get_segments.
    '''
    pass

def get_segments(mpd, hostname, sock, out):
    representations = mpd.representations
    rep = representations[curr_representation]          #assumes curr_representation is index, not actual representation
    byte_range = rep.segment_range(curr_segment_num)

    req = myhttp.HTTPRequest("GET", myhttp.URI(rep.base_url), headers={'Host':hostname, 'Range': 'bytes='+str(byte_range[0])+'-'+str(byte_range[1])})
    (response, raw_body) = issue_request(sock, req)

    #changes
    bytes_in_buffer += byte_range[1] - byte_range[0]
    time_to_pull =

    #fat dictionary
    buffer.append(raw_body)

    return

def stream(hostname, url, out):
    sock = socket.socket()
    sock.connect((hostname, 80))

    # Perform streaming
    mpd = get_mpd(hostname, url, sock)
    get_init(mpd, hostname, sock, out)


    #begin buffering
    seg_ranges = mpd.representations.segment_ranges
    playing=False
    while curr_segment_num <= seg_ranges[len(seg_ranges)-1]:

        if (played_segment_buffer == 0 && segments_in_buffer > join_segments):  #sufficient frames to begin playing
            if not playing :
                start_time = time.time()
                playing == True
            else:
                cur_frame_duration = to_play_buffer[0]['duration']
                if (time.time() - start_time) >= cur_frame_duration):
                    size = to_play_buffer[0]['size']
                    played_segments.add(to_play_buffer.pop(0))
                    played_segment_bytes+=size

                    start_time=time.time()

        #if frames_in_buffer >= buffer_size: #clear the buffer
            # buffer.clear()
        last_buffered=to_play_buffer[-1]
        bandwidth = last_buffered['size']/last_buffered['time_to_pull']

        #bitrate_to_pull <= bandwidth as close as possible
        for representation in mdp.representations.reverse():
            curr_segment=last_buffered['ID']+1
            curr_seg_duration = representation.duration[curr_segment] #will need to check for end of file
            byte_range = representation.segment_range(curr_segment)
            num_bytes = byte_range[1] - byte_range[0]
            if bandwidth > (num_bytes/curr_seg_duration):
                segment=get_segment()
                to_play_buffer.add(segment)
        if max_current_buffer-(bytes_in_buffer-played_segment_bytes) >=:


            # frames_left = max_current_buffer-frames_in_buffer
            # time_to_pull = frames_left/fps
            # max_bits = time_to_pull*bandwidth #maximum number of bits we can pull in a second, because bandwidth is Mb/second
            # bits_per_frame = max_bits/fps # how much data we can pull per frame

            representations=mdp.representations
            #choose highest possible resolution representation based on bits_per_frame.

            get_segments(mpd, hostname, sock, out)
            curr_segment_num += 1
            frames_in_buffer += 1




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
