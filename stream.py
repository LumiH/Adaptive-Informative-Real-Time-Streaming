#!/usr/bin/python3

from argparse import ArgumentParser
import logging
import mympd
import myhttp
import socket
import sys
import threading
import time

logging.basicConfig(stream=sys.stderr,level=logging.DEBUG,format='%(message)s')

to_play_buffer = []
played_segments=[]

#Variables for getting frames
curr_representation = None
curr_frame_displayed_num =0
curr_segment_num =0
last_buffered=None
total_segments=0
prev_bitrate=0


#Variables for deciding when frames are fetched
join_segments =5
buffer_capacity =20000000
max_current_buffer =20000000
bytes_in_buffer =0
segments_in_buffer =0
bandwidth =1000
played_segment_bytes =0

#Variables for playback

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

    return
def update_variables():
    ''' Update the global variables before we call get_segments.
    '''
    pass

def stream(hostname, url, out):
    sock = socket.socket()
    sock.connect((hostname, 80))

    # Perform streaming
    mpd = get_mpd(hostname, url, sock)
    get_init(mpd, hostname, sock, out)
    global last_buffered
    global segments_in_buffer
    global bandwidth
    global total_segments
    global curr_segment_num
    global join_segments

    #begin buffering
    total_segments=len(mpd.representations[0].segment_ranges)
    last_frame = total_segments*(mpd.representations[0]._segment_duration/1000)*fps
    playing=False
    curr_segment_frame=0
    curr_playback_frame=0
    while curr_playback_frame < last_frame:
        print('*'*20)
        print(curr_playback_frame)
        print('*'*20)
        print(segments_in_buffer)
        print('*'*20)
        if segments_in_buffer > join_segments:  #sufficient frames to begin playing
            if not playing :
                start_time = time.time()
                playing = True
            else:

                if ((start_time-time.time())% 1) == 0:     #'plays' certain number of frames every interval
                    curr_playback_frame+=30
                    out.write(to_play_buffer[0]['raw_body'][curr_segment_frame])
                    curr_segment_frame+=1
                if curr_playback_frame > to_play_buffer[0]['frame_number']: #We have played all frames within most recent segment, must move segment from to_play_buffer to played segment
                    size = to_play_buffer[0]['size']
                    played_segments.add(to_play_buffer.pop(0))
                    played_segment_bytes+=size
                    curr_playback_frame=0
                    curr_segment_num=0

        elif segments_in_buffer==0:     #Buffer frames before playing
            segment=get_segment(hostname,sock,mpd.representations[0],0)
            curr_representation=mpd.representations[0]
            to_play_buffer.append(segment)
            segments_in_buffer+=1
        #if frames_in_buffer >= buffer_size: #clear the buffer
            # buffer.clear()
        if len(to_play_buffer)!=0:          #update global variables
            last_buffered=to_play_buffer[-1]
            bandwidth = last_buffered['size']/last_buffered['time_to_pull']
        #bitrate_to_pull <= bandwidth as close as possible

        for representation in mpd.representations:
            curr_segment_num=last_buffered['ID']+1
            if curr_segment_num < total_segments:
                curr_seg_duration = representation._segment_duration #will need to check for end of file
                num_bytes = representation.segment_ranges[curr_segment_num][1]-representation.segment_ranges[curr_segment_num][0]

                if bandwidth > (num_bytes/curr_seg_duration):
                    curr_representation=representation
                    segment=get_segment(hostname,sock,representation,curr_segment_num)
                    to_play_buffer.append(segment)
                    segments_in_buffer+=1

    sock.close()

    print('*'*20)
    print(total_segments)
    print('*'*20)

    return None

def get_segment(hostname,sock,representation,segment):
    global last_buffered
    range_string="bytes="+str(representation.segment_ranges[segment][0])+"-"+str(representation.segment_ranges[segment][1])
    request_start=time.time()
    response, raw_body = issue_request(sock, myhttp.HTTPRequest("GET", representation.base_url, headers={"Host":hostname,"Range":range_string}))
    time_to_pull=time.time()-request_start
    frame_body=[]
    body_size=sys.getsizeof(raw_body)
    number_of_frames = (representation._segment_duration/1000)*fps
    size_per_frame=body_size/number_of_frames
    for i in range(0,number_of_frames/30):
        frame_body.append(raw_body[i*size_per_frame*30:(i+1)*size_per_frame*30])

    segment={'ID':segment,'time_to_pull':time_to_pull,'frame_number':number_of_frames,'size':body_size,'raw_body': frame_body}
    last_buffered=segment
    return segment

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
