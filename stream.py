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
import random
import parser
from math import cos
from math import sin
from math import tan
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
run_start_time=0
delayMax=0.0
delaytype="linear"
LastDelay=0
#Variables for deciding when frames are fetched
join_segments = 1
buffer_capacity =20000000
max_current_buffer =5000000
bytes_in_buffer =0

bandwidth =1000
played_segment_bytes =0

#Variables for playback

fps = 30  #This should be determined by

def issue_request(sock, request,customfield):
    # logging.debug(request)
    print(request)
    global delay
    global delaytype
    global LastDelay

    msg_utf = request.deparse().encode()
    sock.send(msg_utf)

    raw_response = b''
    bufsize = 4096
    LastDelay=float(get_delay(delaytype,customfield))
    print(LastDelay)
    time.sleep(LastDelay)
    new_data = sock.recv(bufsize)
    while b"\r\n" not in new_data:
        time.sleep(LastDelay)
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

def get_delay(type,customfield):
    global delaytype
    global delayMax
    global startime
    if delaytype=="linear":
        return delayMax
    if delaytype=="lineargrowth":
        if total_segments!=0:
            return delayMax*(float(time.time()-run_start_time)/(total_segments*2))
        else:
            return delayMax*(int(time.time()-run_start_time)/(30.0*2.0))
    if delaytype=="sawtooth":
        print(delayMax)
        if bool(random.getrandbits(1)):
            return float(delayMax)
        else:
            return 0.0
    if delaytype=="random":
        return float(random.randint(0,int(delayMax*1000)))/1000.0
    if delaytype=="custom":
        equation=customfield.get()
        code = parser.expr(equation).compile()
        t=int(time.time()-run_start_time)
        print('*'*20)
        print(str(time.time())+","+str(start_time))
        print('*'*20)
        return eval(code)



def get_mpd(hostname, url, sock,customfield):

    req = myhttp.HTTPRequest("GET", myhttp.URI(url), headers={'Host':hostname})

    (response, raw_body) = issue_request(sock, req,customfield)

    mpdfile = mympd.MPDFile(raw_body)

    return mpdfile

def get_init(mpd, hostname, sock, out,customfield):
    req = myhttp.HTTPRequest("GET", myhttp.URI(mpd.initialization_url), headers={'Host':hostname})
    (response, raw_body) = issue_request(sock, req,customfield)
    out.write(raw_body)

    return

def stream(hostname, url, out,TK,framelabel,segmentlabel,vlc_player,reslabel,customfield,delayLabel):

    sock = socket.socket()
    sock.connect((hostname, 80))

    # Perform streaming
    mpd = get_mpd(hostname, url, sock,customfield)
    get_init(mpd, hostname, sock, out,customfield)

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
    global LastDelay



    #begin buffering
    segment_duration=mpd.representations[0]._segment_duration/1000
    total_segments=len(mpd.representations[0].segment_ranges)
    last_frame = total_segments*segment_duration*fps
    curr_segment_frame=0
    representation_chosen=False

    print(running)
    while curr_playback_frame < last_frame and running==True:

        segmentlabel.config(fg="green",text=str(curr_segment_num))
        delayLabel.config(fg="green",text=str(LastDelay))

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
            segment=get_segment(hostname,sock,mpd.representations[0],0,out,reslabel,customfield)
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
                    segment=get_segment(hostname,sock,representation,curr_segment_num,out,reslabel,customfield)
                    to_play_buffer.append(segment)
                    curr_segment_num+=1
                    bytes_in_buffer+=segment['size']
                    representation_chosen=False

        TK.update_idletasks()
        TK.update()
    sock.close()

    return None

def get_segment(hostname,sock,representation,segment,out,reslabel,customfield):
    global last_buffered
    byte_range = representation.segment_ranges[segment]
    range_string='bytes='+str(byte_range[0])+'-'+str(byte_range[1])
    req = myhttp.HTTPRequest("GET", myhttp.URI(representation.base_url), headers={"Host":hostname,"Range":range_string})
    reslabel.config(fg="green",text=str(representation._width)+"x"+str(representation._height))
    request_start=time.time()
    (response, raw_body) = issue_request(sock, req,customfield)
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
    global delayLabel

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

    master = Tk() #creates tkinter instance referenced thorghout

    vlc_instance = vlc.Instance("--width=5000, height=10000")
    fpath = os.path.join(os.getcwd(), "test.mp4")
    vlc_player = vlc_instance.media_new(fpath).player_new_from_media()

    def start(): #Assigns chosen values to global variables and initiates streaming

        global running
        global max_current_buffer
        global curr_playback_frame
        global playing
        global delay
        global run_start_time
        global delaytype
        global delayMax


        running=True

        if curr_playback_frame>0: #if paused and not restarted begin playback immediatley
            playing=True

        raw_MCB=e.get()
        max_current_buffer=int(e.get()*1000000)
        join_segments=int(j.get())
        delayMax=float(k.get())/1000.0

        print("Running simulation with MCB:"+str(raw_MCB)+"Mb and join_segments:"+str(join_segments)+"Delay Type:"+str(delaytype)+"Max delay"+str(delayMax))
        run_start_time=time.time()

        stream(uri.host, uri.abs_path, sink,master,TimeDynamic,SegDynamic,vlc_player,ResDynamic,CustomEquation,delayDynamic)

        #Unpauses VLC playback
        if not vlc_player.is_playing():
            vlc_player.set_pause(False)



        master.update()
        # print("test")
    def stop(): #Pauses the stream by stoping playback

        global running
        global playing

        running=False #total program running
        playing=False #playback occuring in VlC

        print("PAUSED")

        #sets text color to yellow to indicate paused state
        TimeDynamic.config(fg="yellow")
        SegDynamic.config(fg="yellow")

        ResDynamic.config(fg="yellow")
        delayDynamic.config(fg="yellow")

        #Puases the Vlc playback
        if vlc_player.is_playing():
            print ("-"*30 + "Success!"+"-"*30 )
            vlc_player.set_pause(True)


    def restart(): #processes the user restart request and sets variables to default

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

        #pauses vlc playback
        if vlc_player.is_playing():
            vlc_player.set_pause(True)
        vlc_player.stop()

        #sets real time variable text color to indicate stopping
        TimeDynamic.config(fg="red",text="00:00:00")
        SegDynamic.config(fg="red",text="0")
        delayDynamic.config(fg="red",text="0")
        ResDynamic.config(fg="red",text="0x0")
        print("RESET")


    def setdelay(type): #assignes the delay type from the buttons to the global variable

        global delaytype
        delaytype=type

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
    ResDynamic = Label(master,text="Max Request Delay (ms)",fg="black")
    ResDynamic.pack()
    k=Scale(master, from_=0, to=2500,  orient=HORIZONTAL)
    k.pack()
    k.set(0.0)
    #delay time buttons
    linear=Button(master, text="Linear Max",command=lambda: setdelay("linear"))
    random=Button(master, text="random", command=lambda: setdelay("random"))
    lineargrowth=Button(master, text="Linear Growth", command=lambda: setdelay("lineargrowth"))
    sawtooth=Button(master, text="Sawtooth",command=lambda:setdelay("sawtooth"))
    custom=Button(master, text="Custom",command=lambda:setdelay("custom"))
    CustomLabel=Label(master,text="Custom Delay Equation(must be a function of t)")
    CustomEquation = Entry(master)

    linear.pack()
    random.pack()
    lineargrowth.pack()
    sawtooth.pack()
    custom.pack()
    CustomLabel.pack()
    CustomEquation.pack()
    CustomEquation.insert(0,"ex. 3x,sin(x)**2")
    #start and stop buttons
    b = Button(master, text="Run", command=lambda : start())
    s= Button(master, text="Pause", command=lambda: stop())
    r= Button(master, text="Restart",command=lambda: restart())
    b.pack()
    s.pack()
    r.pack()
    #Real Time Readouts
    TimeLabel = Label(master,text="Playback Time",fg="black")
    TimeLabel.pack()
    TimeDynamic=Label(master,text="00:00:00",fg="red")
    TimeDynamic.pack()
    SegLabel = Label(master,text="Last Segment Buffered",fg="black")
    SegLabel.pack()
    SegDynamic=Label(master,text="0",fg="red")
    SegDynamic.pack()
    ResLabel=Label(master,text="Current Resolution",fg="black")
    ResLabel.pack()
    ResDynamic = Label(master,text="0x0",fg="red")
    ResDynamic.pack()
    delayLabel=Label(master,text="Current Delay",fg="black")
    delayLabel.pack()
    delayDynamic=Label(master,text="0",fg="red")
    delayDynamic.pack()

    mainloop()



    if settings.output is not None:
        sink.close()

if __name__ == '__main__':
    main()
