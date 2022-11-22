"""
play.py, uses the sounddevice library to play multiple audio files to multiple output devices at the same time
Written by Ivano Selvaggi
"""

import sounddevice
import soundfile
import threading
import os

from threading import Thread

#from jproperties import Properties

import argparse


class PlaySoundThread(Thread):

    data = None
    fs = None
    current_frame = 0
    device = None
    event = threading.Event()

    def __init__(self, device, filename, basepath):
        super().__init__(None, None, None, None, None)
        self.data, self.fs = soundfile.read(basepath + "\\" + filename)
        self.device = device
        self.filename = filename


    def callback(self, outdata, frames, time, status):
        if status:
            print(status)
        chunksize = min(len(self.data) - self.current_frame, frames)
        outdata[:chunksize] = self.data[self.current_frame:self.current_frame + chunksize]
        if chunksize < frames:
            outdata[chunksize:] = 0
            raise sounddevice.CallbackStop()
        self.current_frame += chunksize

    def run(self):
        stream = sounddevice.OutputStream(
            samplerate=self.fs, device=self.device["index"], channels=self.data.shape[1],
            callback=self.callback, finished_callback=self.event.set
        )
        with stream:
            self.event.wait()  # Wait until playback is finished

    def stop(self):
        self.event.set()


def get_output_device_name(info):
    return info["name"] + ", " + sounddevice.query_hostapis(index = info["hostapi"])["name"]


def find_output_device_name(index_info):
    """
    Given a device dict, return True if the device is one of our USB sound cards and False if otherwise
    :param index_info: a device info dict from PyAudio.
    :return: True if usb sound card, False if otherwise
    """

    index, info = index_info

    if info["max_output_channels"] > 0:
        return get_output_device_name(info)
    return False


if __name__ == "__main__":

    #print(sounddevice.query_hostapis())
    #print(sounddevice.query_devices()) #device="", kind="output"
    #for index_info in sounddevice.query_devices():
    #    print(index_info)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '-l', '--list-devices', action='store_true',
        help='show list of audio devices and exit')
    parser.add_argument(
        '-f', '--find-devices',
        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:

        sound_card = list(filter(lambda x: x is not False,
                                            map(find_output_device_name,
                                                [index_info for index_info in enumerate(sounddevice.query_devices())])))
        for dev in sound_card:
            print(dev)

        parser.exit(0)
    if args.find_devices:

        sound_card = list(filter(lambda info: args.find_devices in info["name"] and info["max_output_channels"] > 0,
                                            sounddevice.query_devices()))
        for dev in sound_card:
            print(get_output_device_name(dev))

        parser.exit(0)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser])
    parser.add_argument(
        'filename', metavar='FILENAME',
        help='audio file to be played back')
    args = parser.parse_args(remaining)


    threads = []

    fullpath = os.path.dirname(os.path.abspath(args.filename))
    #configs = Properties()
    #with open(args.filename, 'rb') as config_file:
    #    configs.load(config_file)

    with open(args.filename, 'r') as config_file:
        lines = config_file.readlines()
    for line in lines:
        item = line.replace("\n\r", "").split("=")
        # print(item[0].replace("\ ", " ") + " " + item[1]) #item[1].data
        device = sounddevice.query_devices(device=item[1], kind="output")
        #print(device)
        threads.append(PlaySoundThread(device, item[0].replace("\ ", " ") , fullpath))


    running = True

    print("Playing files")

    for thread in threads:
        print("Play", thread.filename, "to", thread.device["name"])
        thread.start()

    while running:

        try:
            for thread in threads:
                # print("Waiting for device", device_index, "to finish")
                thread.join(1)

            for thread in threads.copy():
                if not thread.is_alive():
                    threads.remove(thread)

            if not threads:
                running = False

        except KeyboardInterrupt:
            running = False
            print("Stopping threads")
            for thread in threads:
                thread.stop()
            print("Threads stopped")

    print("Finish")


