from stmpy import Machine, Driver

import paho.mqtt.client as mqtt
import stmpy
import logging
from threading import Thread
import json

from os import system
import os
import time

import pyaudio
import wave

MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

MQTT_TOPIC_INPUT = 'ttm4115/team_07/command'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_07/answer'

class Recorder:
    def __init__(self):
        self.recording = False
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 2
        self.fs = 44100  # Record at 44100 samples per second
        self.filename = "output.wav"
        self.p = pyaudio.PyAudio()

        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

    def record(self):
        print("starting")
        self._logger.info('Starting')
        stream = self.p.open(format=self.sample_format,
                channels=self.channels,
                rate=self.fs,
                frames_per_buffer=self.chunk,
                input=True)
        self.frames = []  # Initialize array to store frames
        # Store data in chunks for 3 seconds
        self.recording = True
        while self.recording:
            data = stream.read(self.chunk)
            self.frames.append(data)
        print("done recording")
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Terminate the PortAudio interface 
        # (This leads to only one recodring being possible, commented out for now)
        # self.p.terminate()

    def stop(self):
        print("stopping")
        self.recording = False

    def process(self):
        print("processing")
        # Save the recorded data as a WAV file
        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        print("finished processing")


recorder = Recorder()
_logger = logging.getLogger(__name__)

# statmachine driver
t0 = {'source': 'initial', 'target': 'ready'}
t1 = {'trigger': 'start', 'source': 'ready', 'target': 'recording'}
t2 = {'trigger': 'done', 'source': 'recording', 'target': 'processing'}
t3 = {'trigger': 'done', 'source': 'processing', 'target': 'ready'}

s_recording = {'name': 'recording', 'do': 'record()', "stop": "stop()"}
s_processing = {'name': 'processing', 'do': 'process()'}


stm = Machine(name='stm', transitions=[t0, t1, t2, t3], states=[s_recording, s_processing], obj=recorder)
recorder.stm = stm

driver = Driver()
driver.add_machine(stm)
driver.start()


# MQTT client
def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:
            _logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            return
        command = payload.get('command')
        _logger.debug('Command in message is {}'.format(command))
        if command == "start": driver.send('start', 'stm')
        elif command == "stop": driver.send('stop', 'stm')

def on_connect(client, userdata, flags, rc):
       _logger.debug('MQTT connected to {}'.format(client))

# create a new MQTT client
mqtt_client = mqtt.Client()
# callback methods
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
# Connect to the broker
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
# subscribe to proper topic(s) of your choice
mqtt_client.subscribe(MQTT_TOPIC_INPUT)
# start the internal loop to process MQTT messages
mqtt_client.loop_start()
