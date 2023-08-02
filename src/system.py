import RPi.GPIO as GPIO
import traceback
import os
import re
import time

KRAKEN_POWER_RELAY_PIN_BCM = 27


def kraken_sdr_power_off():
    timeout = 10
    start = time.time()
    stop_kraken_service()
    while is_kraken_service_running():
        if time.time() - start > timeout:
            raise Exception('Kraken service have not stopped in time')
        time.sleep(0.1)
    start = time.time()
    turn_kraken_sdr_relay_off()
    while is_kraken_sdr_connected():
        if time.time() - start > timeout:
            raise Exception('Kraken SDR have not disconnected in time. Is the on/off relay connected correctly?')
        time.sleep(0.1)


def kraken_sdr_power_on():
    timeout = 15
    start = time.time()
    turn_kraken_sdr_relay_on()
    while not is_kraken_sdr_connected():
        if time.time() - start > timeout:
            raise Exception('Kraken SDR have not connected in time')
        time.sleep(0.1)
    start = time.time()
    start_kraken_service()
    while not is_kraken_service_running():
        if time.time() - start > timeout:
            raise Exception('Kraken service have not started in time')
        time.sleep(0.1)


def turn_kraken_sdr_relay_off():
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(KRAKEN_POWER_RELAY_PIN_BCM, GPIO.OUT)
    GPIO.output(KRAKEN_POWER_RELAY_PIN_BCM, GPIO.LOW)


def turn_kraken_sdr_relay_on():
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(KRAKEN_POWER_RELAY_PIN_BCM, GPIO.OUT)
    GPIO.output(KRAKEN_POWER_RELAY_PIN_BCM, GPIO.HIGH)


def is_kraken_sdr_connected() -> bool:
    start = time.time()
    cmd_lines = os.popen("lsusb")
    for line in cmd_lines:
        if re.match(r'^.+RTL2838.+$', line):
            print(f'is_kraken_sdr_connected took {time.time() - start} seconds')
            return True
    print(f'is_kraken_sdr_connected took {time.time() - start} seconds')
    return False


def is_kraken_service_running() -> bool:
    start = time.time()
    cmd_lines = os.popen("sudo systemctl status krakensdr.service")
    r_active = r'^.+Active.+active.+running.+$'
    r_dead = r'^.+Active.+inactive.+dead.+$'
    for line in cmd_lines:
        if re.match(r_active, line):
            print(f'is_kraken_service_running took {time.time() - start} seconds')
            return True
        if re.match(r_dead, line):
            return False
    print(f'is_kraken_sdr_connected took {time.time() - start} seconds')
    return False


def start_kraken_service():
    os.popen("sudo systemctl start krakensdr.service")


def stop_kraken_service():
    os.popen("sudo systemctl stop krakensdr.service")


