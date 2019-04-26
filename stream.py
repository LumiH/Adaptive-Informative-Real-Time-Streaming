#!/usr/bin/python3

from argparse import ArgumentParser
import logging
import mympd
import myhttp
import socket
import sys
import threading
import time
from tkinter import *
import datetime
import os
import vlc

to_play_buffer = []
played_segments=[]

#Variables for getting frames
curr_representation = None
curr_segment_num =0
curr_segment_frame=0
last_buffered=None
total_segments=0
running=False
playing=False
curr_playback_frame=0
start_time=0
delay=0

#Variables for deciding when frames are fetched
join_segments = 1
buffer_capacity =20000000
max_current_buffer =5000000
bytes_in_buffer =0

bandwidth =1000
played_segment_bytes =0

#Variables for playback

fps = 30  #This should be determined by

def issue_request(sock, request):
    # logging.debug(request)
    print(request)
    global delay
    msg_utf = request.deparse().encode()
    sock.send(msg_utf)

    raw_response = b''
    bufsize = 4096
    time.sleep(delay)
    new_data = sock.recv(bufsize)
    while b"\r\n" not in new_data:
        time.sleep(delay)
        raw_response += new_data
        new_data = sock.recv(bufsize)

    raw_response += new_data

    # Parse response header
    end_header = raw_response.index(b'\r\n\r\n') + 4
    raw_header = raw_response[:end_header]
    #logging.debug(raw_header)
    response = myhttp.HTTPResponse.parse(raw_header.decode())
    #logging.debug(response)

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

def stream(hostname, url, out,TK,framelabel,segmentlabel,vlc_player):

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
    global played_segment_bytes
    global bytes_in_buffer
    global running
    global playing
    global start_time
    global curr_playback_frame

    #begin buffering
    segment_duration=mpd.representations[0]._segment_duration/1000
    total_segments=len(mpd.representations[0].segment_ranges)
    last_frame = total_segments*segment_duration*fps
    curr_segment_frame=0
    representation_chosen=False

    print(running)
    while curr_playback_frame < last_frame and running==True:

        segmentlabel.config(fg="green",text=str(curr_segment_num))


        if len(to_play_buffer) > join_segments and playing!=True:  #handles transfer of frames to playback
            playing=True
            start_time=time.time()
        if playing==True:
            # print(curr_playback_frame)
            framelabel.config(fg="green",text=str(datetime.timedelta(seconds=(curr_playback_frame)/fps)))
            new_playback_frame=int(float(time.time()-start_time)/(1.0/fps))
            curr_segment_frame+=new_playback_frame-curr_playback_frame
            curr_playback_frame=new_playback_frame
            # print(curr_segment_frame)
            if curr_segment_frame >= to_play_buffer[0]['frame_number']:
                played_segments.append(to_play_buffer.pop(0))
                played_segment_bytes+=to_play_buffer[0]['size']
                curr_segment_frame=0
        if len(to_play_buffer) == 0:     #get initial segment of data
            framelabel.config(fg="red",text=str(datetime.timedelta(seconds=(curr_playback_frame)/fps)))
            segment=get_segment(hostname,sock,mpd.representations[0],0,out)
            curr_representation = mpd.representations[0]
            to_play_buffer.append(segment)
            curr_segment_num+=1
            bytes_in_buffer+=segment['size']
            representation_chosen=False
            vlc_player.play()

        #if frames_in_buffer >= buffer_size: #clear the buffer
            # buffer.clear()

        else: # update global variables and get segment
            last_buffered = to_play_buffer[-1]
            bandwidth = last_buffered['size']/last_buffered['time_to_pull']

            if curr_segment_num < total_segments:
                if representation_chosen!=True:
                    for representation in reversed(mpd.representations):
                            curr_seg_duration = representation._segment_duration
                            num_bytes = representation.segment_ranges[curr_segment_num][1]-representation.segment_ranges[curr_segment_num][0]

                            if bandwidth > (num_bytes/float(curr_seg_duration/1000)):

                                curr_representation = representation
                                representation_chosen=True
                                break
                    if representation_chosen==False:
                        curr_representation=mpd.representations[0]
                        representation_chosen=True
                elif max_current_buffer - (bytes_in_buffer - played_segment_bytes) > num_bytes:
                    # print('*'*20)
                    # print(curr_segment_num, total_segments)
                    # print('*'*20)
                    segment=get_segment(hostname,sock,representation,curr_segment_num,out)
                    to_play_buffer.append(segment)
                    curr_segment_num+=1
                    bytes_in_buffer+=segment['size']
                    representation_chosen=False

        TK.update_idletasks()
        TK.update()
    sock.close()

    return None

def get_segment(hostname,sock,representation,segment,out):
    global last_buffered
    byte_range = representation.segment_ranges[segment]
    range_string='bytes='+str(byte_range[0])+'-'+str(byte_range[1])
    req = myhttp.HTTPRequest("GET", myhttp.URI(representation.base_url), headers={"Host":hostname,"Range":range_string})

    request_start=time.time()
    (response, raw_body) = issue_request(sock, req)
    out.write(raw_body)
    # print("WRITE")

    time_to_pull=time.time()-request_start
    # print(time_to_pull)
    body_size=sys.getsizeof(raw_body)
    number_of_frames = (representation._segment_duration/1000)*fps

    segment_pack={'ID':segment,'time_to_pull':time_to_pull,'frame_number':number_of_frames,'size':body_size,'raw_body': raw_body}

    last_buffered = segment_pack
    return segment_pack

def main():
    global running
    global total_segments


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

    master = Tk()

    vlc_instance = vlc.Instance("--width=5000, height=10000")
    fpath = os.path.join(os.getcwd(), "test.mp4")
    vlc_player = vlc_instance.media_new(fpath).player_new_from_media()

    def start():

        global running
        global max_current_buffer
        global curr_playback_frame
        global playing
        global delay
        running=True
        if curr_playback_frame>0:
            playing=True
        raw_MCB=e.get()
        max_current_buffer=int(e.get()*1000000)
        join_segments=int(j.get())
        delay=float(k.get())/1000.0
        print("Running simulation with MCB:"+str(raw_MCB)+"Mb and join_segments:"+str(join_segments))
        stream(uri.host, uri.abs_path, sink,master,label2,label6, vlc_player)
        if not vlc_player.is_playing():
            vlc_player.set_pause(False)
        master.update()
        # print("test")
    def stop():
        global running
        global playing
        running=False
        playing=False
        print("Paused")
        label2.config(fg="yellow")
        label6.config(fg="yellow")
        if vlc_player.is_playing():
            print ("-"*30 + "Success!"+"-"*30 )
            vlc_player.set_pause(True)

    def restart():
        global running
        global last_buffered
        global segments_in_buffer
        global bandwidth
        global total_segments
        global curr_segment_num
        global join_segments
        global played_segment_bytes
        global bytes_in_buffer
        global running
        global curr_playback_frame
        global to_play_buffer

        join_segments = int(j.get())
        max_current_buffer =int(e.get()*1000000)
        bytes_in_buffer =0
        bandwidth =1000
        played_segment_bytes =0
        running=False
        to_play_buffer=[]
        curr_representation = None
        curr_segment_num =0
        last_buffered=None
        total_segments=0
        curr_playback_frame=0
        if vlc_player.is_playing():
            vlc_player.set_pause(True)
        vlc_player.stop()
        label2.config(fg="red",text="00:00:00")
        label6.config(fg="red",text="0")
        print("RESET")
    #scale slider for max_current_buffer
    label = Label(master,text="Maximum active buffer (Mb)",fg="black")
    label.pack()
    e = Scale(master, from_=0, to=20,  orient=HORIZONTAL)
    e.pack()
    e.set(5)
    #scale slider for join segments
    label3 = Label(master,text="Join segments",fg="black")
    label3.pack()
    j=Scale(master, from_=0, to=30,  orient=HORIZONTAL)
    j.pack()
    j.set(1)
    #scale slider for delay
    label7 = Label(master,text="Request delay (ms)",fg="black")
    label7.pack()
    k=Scale(master, from_=0, to=2500,  orient=HORIZONTAL)
    k.pack()
    k.set(0.0)
    #start and stop buttons
    b = Button(master, text="Run", command=lambda : start())
    s= Button(master, text="Pause", command=lambda: stop())
    r= Button(master, text="Restart",command=lambda: restart())
    b.pack()
    s.pack()
    r.pack()
    #current frame rate and segment number labels
    label4 = Label(master,text="Playback Time",fg="black")
    label4.pack()
    label2=Label(master,text="00:00:00",fg="red")
    label2.pack()
    label5 = Label(master,text="Last Segment Buffered",fg="black")
    label5.pack()
    label6=Label(master,text="0",fg="red")
    label6.pack()

    mainloop()


    # b = Button(master, text="OK",command=stream(uri.host, uri.abs_path, sink))


    if settings.output is not None:
        sink.close()

if __name__ == '__main__':
    main()
