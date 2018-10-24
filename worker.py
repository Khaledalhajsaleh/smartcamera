
# Worker process for smartcam devices

import base64
import json
import os
import random
import time

# force keras backend:
os.environ['KERAS_BACKEND'] = 'theano'
import keras
from scipy.misc import imread

from lees_gps import get_location

#start gps deamon
pi_id = 'o3u43u'
os.system('sudo gpsd -n /dev/ttyS0 -F /var/run/gpsd.sock')

#load the model
model = keras.models.load_model('model')

def run(logger):
    while True:
        print('doing one batch of work')

        #get time
        t = time.localtime()
        time_string = str(t.tm_year) + '-' + str(t.tm_yday) + '-' + str(t.tm_hour) + '-' + str(t.tm_min) + '-' + str(t.tm_sec)

        #get photo
        file_name_image = 'test.jpg'
        command = 'raspistill -o ' + file_name_image + ' -w 1024 -h 1024 --nopreview -t 2000'
        os.system(command)
        photo = imread(file_name_image)

        #get location
        location_string = str(get_location)

        #apply a random condition, later on this conditon is based on model applied to photo
        if random.randint(0, 10) == 5:
            with open(file_name_image, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
            #information to be sent
            to_sent = {'photo': encoded_string,
                       'time': time_string,
                       'location':location_string,
                       'filename': "%s_%s_%s" % (pi_id, time_string, location_string)
                      }

            #construct json
            to_sent = json.dumps(to_sent)
