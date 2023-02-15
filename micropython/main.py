#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2021-2022 Przemyslaw Bereski https://github.com/przemobe/

from machine import Pin, SPI, I2C
import Ntw
import time
import ustruct
from imu import MPU6050
from fusion import Fusion


class PeriodicUdpSender:
    def __init__(self, ntw, tgt_addr, tgt_port, period_sec):
        self.ntw = ntw
        self.tgt_addr = bytes(tgt_addr)
        self.tgt_port = tgt_port
        self.period_sec = period_sec
        # Define states: 0 - idle, 1 - connecting, 2 - connected
        self.state = 0
        self.init_time = 0

    def loop(self, data):
        ctime = time.time()
        self.data = data
        # State - idle
        if 0 == self.state:
            if not self.ntw.isIPv4Configured():
                return
            print('Connecting...')
            self.ntw.connectIp4(self.tgt_addr)
            self.init_time = ctime
            self.state = 1

        # State - connecting
        elif 1 == self.state:
            if self.ntw.isConnectedIp4(self.tgt_addr):
                print('Connected')
                self.init_time = ctime
                self.state = 2
                self.send_data()
            elif ctime - self.init_time > 3:
                self.state = 0

        # State - connected
        else:  # 2 == self.state
            if ctime - self.init_time > self.period_sec:
                self.send_data()
                self.init_time += self.period_sec

    def send_data(self):
        n = self.ntw.sendUdp4(self.tgt_addr, self.tgt_port, self.data)
        if 0 > n:
            print(f'Fail to send data error={n}')
        else:
            print('Data sent')


def create_packet():
    bin_values = []
    name = ['yaw', 'pitch', 'roll']
    fuse.update_nomag(imu.accel.xyz, imu.gyro.xyz)
    resources = [fuse.heading, fuse.pitch, fuse.roll]
    # encode values
    for comment, value in zip(name, resources):
        # print(f'{comment}:', *[k for k in values])
        bin_values.append(ustruct.pack('f', value))
    bin_string = flag + b''.join(bin_values)
    return bin_string


if __name__ == '__main__':
    # Create network
    nicSpi = SPI(0, baudrate=10000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    nicCsPin = Pin(5)
    ntw = Ntw.Ntw(nicSpi, nicCsPin)

    # create MPU6050 object
    imu = MPU6050(I2C(0, sda=Pin(0), scl=Pin(1), freq=400000))
    fuse = Fusion()
    flag = b'\x00\x02'

    # Set static IP address
    ntw.setIPv4([192,168,100,2], [255,255,255,252], [192,168,100,1])

    # Create periodic sender
    sender = PeriodicUdpSender(ntw, [192,168,1,148], 5555, 0.5)

    while True:
        ntw.rxAllPkt()
        sender.loop(create_packet())
