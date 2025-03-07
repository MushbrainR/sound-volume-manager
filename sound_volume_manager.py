import numpy as np
import sounddevice as sd
import subprocess
import time
import logging
from threading import Timer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Constants
THRESHOLD = 0.4    # Adjust this threshold value according to your needs
REDUCE_VOLUME = 10  # How much to reduce the volume in percentage
SAMPLE_RATE = 44100
DURATION = 1  # Duration to check sound levels (seconds)
RESTORE_DELAY = 7  # Delay in seconds before restoring the volume
COOLDOWN = 5  # Cooldown period in seconds to prevent rapid volume changes

# State variables
last_volume = None
last_reduction_time = 0


def get_volume():
    try:
        output = subprocess.check_output(["osascript", "-e", "output volume of (get volume settings)"])
        return int(output.strip())
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting volume: {e}")
        return None


def set_volume(volume):
    try:
        subprocess.call(["osascript", "-e", f"set volume output volume {volume}"])
        logging.info(f"Volume set to: {volume}%")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error setting volume: {e}")


def restore_volume():
    global last_volume
    if last_volume is not None:
        set_volume(last_volume)
        last_volume = None


def callback(indata, frames, time_info, status):
    global last_volume, last_reduction_time
    if status:
        logging.warning(status)
    volume_norm = np.linalg.norm(indata) * 10
    current_time = time.time()

    if volume_norm > THRESHOLD and (current_time - last_reduction_time) > COOLDOWN:
        logging.info(f"Loud sound detected: {volume_norm}")
        current_volume = get_volume()
        if current_volume is not None and last_volume is None:
            last_volume = current_volume
            new_volume = max(current_volume - REDUCE_VOLUME, 0)
            set_volume(new_volume)
            last_reduction_time = current_time
            Timer(RESTORE_DELAY, restore_volume).start()


try:
    with sd.InputStream(callback=callback, channels=1, samplerate=SAMPLE_RATE):
        logging.info("Listening for loud sounds...")
        while True:
            time.sleep(DURATION)
except Exception as e:
    logging.error(f"An error occurred: {e}")
finally:
    logging.info("Script terminated.")
