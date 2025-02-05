import RPi.GPIO as gp
import os
import time
import signal
import sys

# ~ #actuator library and units
from zaber_motion import Library, Units
from zaber_motion.ascii import Connection
Library.enable_device_db_store()  

with Connection.open_serial_port("/dev/ttyUSB0") as connection:
    device_list = connection.detect_devices()
    print("Found {} devices".format(len(device_list)))
    #homing the actuator
    device = device_list[0] #get the device
    axis = device.get_axis(1) #get the axis
    axis.settings.set("maxspeed", 20, Units.VELOCITY_MILLIMETRES_PER_SECOND) #set to gentle maximum speed
    axis.settings.set("motion.accelonly",2,Units.NATIVE) #set to gentle acceleration
    #accelonly = axis.settings.get("motion.accelonly", Units.NATIVE) ### example command to find value of motion parameter, can be printed with print()
    axis.settings.set("motion.decelonly",2,Units.NATIVE) #set to gentle deceleration
    print("Resetting the actuator position")
    axis.home()
    #axis.move_relative(135, Units.LENGTH_MILLIMETRES) #for test only
    #axis.home() #for test only
    print("Moving to the first row")
    time.sleep(5)  #waiting for 10  seconds
    ##The value in the command below defines how far actuator travels up to the first row of wellplates, if not the home positoin
    axis.move_relative(4, Units.LENGTH_MILLIMETRES) ### NOTE THAT I ANTICIPATE HOME IS THE CORRECT STARTING POS, so this is commented




def setup():
    gp.cleanup() # Cleanup the GPIO pins in case someone was not nice and didn't clean them up
    gp.setwarnings(True)
    gp.setmode(gp.BOARD)
    gp.setup(7, gp.OUT)
    gp.setup(11, gp.OUT)
    gp.setup(12, gp.OUT)
    gp.setup(15, gp.OUT)
    gp.setup(16, gp.OUT)
    gp.setup(21, gp.OUT)
    gp.setup(22, gp.OUT)
    gp.output(11, True)
    gp.output(12, True)
    gp.output(15, True)
    gp.output(16, True)
    gp.output(21, True)
    gp.output(22, True)
    
    

def cleanup(*args):
    print('Cleaning up')
    gp.cleanup() # Cleanup our GPIO pins so they can be used by others
    print('All done!')
    sys.exit(0)


# Tells the program what function to run on interrupts and terminations
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


# Constants used by the program
NUMBER_OF_IMAGES_TO_TAKE = 3
IMAGE_OUTPUT_DIRECTORY = '/home/minor/Documents/ImagingSystem/' #REMOVE alyssasimages FROM DIRECTORY WHEN RUNNING FOR REAL. THIS IS TO NOT DISRUPT EXP PICS
#IMAGE_OUTPUT_DIRECTORY = '/home/minor/Documents/ImagingSystem/' #
CAMERA_LETTERS = ['A', 'B', 'C', 'D']

# This is a way for us to map the camera letter to a number that libcamera understands
camera_letter_to_number = {
    'A': 0,
    'B': 1,
    'C': 2,
    'D': 3
}


# Starts the camera that is passed into the function
def start_camera(camera_letter):
        if camera_letter == 'A':
            print("Starting camera A")
            gp.output(7, False)
            gp.output(11, False)
            gp.output(12, True)
        elif camera_letter == 'B':
            print("Starting camera B")
            gp.output(7, True)
            gp.output(11, False)
            gp.output(12, True)
        elif camera_letter == 'C':
            print("Starting camera C")
            gp.output(7, False)
            gp.output(11, True)
            gp.output(12, False)
        elif camera_letter == 'D':
            print("Starting camera D")
            gp.output(7, True)
            gp.output(11, True)
            gp.output(12, False)
        else:
            print('Letter should be A, B, C, or D. Unrecognized camera letter provided: ', camera_letter)
        

# Takes a still using the camera corresponding to the letter given and outputs it in the specified output directory
def take_still(camera_letter, output_directory):
    timestamped_image = "{camera_letter}-image-{timestamp}.jpg".format(camera_letter=camera_letter, timestamp=time.strftime("%Y%m%d-%H%M%S"))
    output_file_path = "{output_directory}/camera{camera_letter}/{timestamped_image}".format(output_directory=output_directory, camera_letter=camera_letter, timestamped_image=timestamped_image)
    capture_image_command = "sudo libcamera-still -t 10000 --camera {camera_num} -o {output_file_path}".format(camera_num=camera_letter_to_number[camera_letter], output_file_path=output_file_path)
    os.system(capture_image_command) # Runs the command for us


def main():
    setup() # Run any required setup to before taking pictures
    for camera_letter in CAMERA_LETTERS:
        start_camera(camera_letter)
        for image_number in range(0, NUMBER_OF_IMAGES_TO_TAKE):
            print("Capturing image {image_number} for camera {camera_letter}".format(image_number=image_number, camera_letter=camera_letter))
            take_still(camera_letter, IMAGE_OUTPUT_DIRECTORY)


## This is what calls main and runs the program
#if __name__ == "__main__":
#    main()

#i range defines how many rows you have on a transparent stage (e.g. range (0,5) means 5 rows will be imaged)
for i in range (0,5): 
    if __name__ == "__main__":
        main()
    
    if i == 4: break #No action in the last step. i should be (range-1) 
    print("Waiting")
    time.sleep(0)  #waiting for 0 seconds
    print("Ready for the next round")
    #code of moving linear actuator
    with Connection.open_serial_port("/dev/ttyUSB0") as connection:
         device_list = connection.detect_devices()
         print("Found {} devices".format(len(device_list)))
         print("Moving to next row")
         device = device_list[0]
         axis = device.get_axis(1)
         axis.settings.set("maxspeed", 20, Units.VELOCITY_MILLIMETRES_PER_SECOND) #set to gentle maximum speed, these should not have to be reset from above, but jic
         axis.settings.set("motion.accelonly",2,Units.NATIVE) #set to gentle acceleration
         axis.settings.set("motion.decelonly",2,Units.NATIVE) #set to gentle deceleration
         axis.move_relative(128, Units.LENGTH_MILLIMETRES)  #change back to 128 after set
    print("Waiting to settle")
    time.sleep(1)  #waiting for 1 seconds


###     Section below is to cover the second and the third stage.
###     If your experiment does not extend to the second or the third experiment comment this part out until "Going Home" command
print("Moving to the second stage")
with Connection.open_serial_port("/dev/ttyUSB0") as connection:
     device_list = connection.detect_devices()
     device = device_list[0]
     axis = device.get_axis(1)
     axis.move_relative(128, Units.LENGTH_MILLIMETRES) #space between the 5th row the first stage and the first row of the second stage; 210 in TO code

#i range defines how many rows you have on a transparent stage (e.g. range (0,5) means 5 rows will be imaged)
for i in range (0,5): 
    if __name__ == "__main__":
        main()
    
    if i == 4: break #No action in the last step. i should be (range-1) 
    print("Waiting")
    time.sleep(0)  #waiting for 0 seconds
    print("Ready for the next round")
    #code of moving linear actuator
    with Connection.open_serial_port("/dev/ttyUSB0") as connection:
         device_list = connection.detect_devices()
         print("Found {} devices".format(len(device_list)))
         print("Moving to next row")
         device = device_list[0]
         axis = device.get_axis(1)
         axis.settings.set("maxspeed", 20, Units.VELOCITY_MILLIMETRES_PER_SECOND) #set to gentle maximum speed, these should not have to be reset from above, but jic
         axis.settings.set("motion.accelonly",2,Units.NATIVE) #set to gentle acceleration
         axis.settings.set("motion.decelonly",2,Units.NATIVE) #set to gentle deceleration
         axis.move_relative(128, Units.LENGTH_MILLIMETRES)  #this was set to 13.5 in Toronto code bgut we don't have acetal rods between plates 
    print("Waiting to settle")
    time.sleep(1)  #waiting for 1 seconds

###     Section below is to cover the second and the third stage.
###     If your experiment does not extend to the second or the third experiment comment this part out until "Going Home" command
print("Moving to the THIRD stage")
with Connection.open_serial_port("/dev/ttyUSB0") as connection:
     device_list = connection.detect_devices()
     device = device_list[0]
     axis = device.get_axis(1)
     axis.move_relative(252, Units.LENGTH_MILLIMETRES) #space between the 5th row the first stage and the first row of the second stage; 210 in TO code

#i range defines how many rows you have on a transparent stage (e.g. range (0,5) means 5 rows will be imaged)
for i in range (0,5): 
    if __name__ == "__main__":
        main()
    
    if i == 4: break #No action in the last step. i should be (range-1) 
    print("Waiting")
    time.sleep(0)  #waiting for 0 seconds
    print("Ready for the next round")
    #code of moving linear actuator
    with Connection.open_serial_port("/dev/ttyUSB0") as connection:
         device_list = connection.detect_devices()
         print("Found {} devices".format(len(device_list)))
         print("Moving to next row")
         device = device_list[0]
         axis = device.get_axis(1)
         axis.settings.set("maxspeed", 20, Units.VELOCITY_MILLIMETRES_PER_SECOND) #set to gentle maximum speed, these should not have to be reset from above, but jic
         axis.settings.set("motion.accelonly",2,Units.NATIVE) #set to gentle acceleration
         axis.settings.set("motion.decelonly",2,Units.NATIVE) #set to gentle deceleration
         axis.move_relative(128, Units.LENGTH_MILLIMETRES)  #this was set to 13.5 in Toronto code bgut we don't have acetal rods between plates 
    print("Waiting to settle")
    time.sleep(1)  #waiting for 1 seconds

print("Going Home")
#code for taking the actuator the rest position below
with Connection.open_serial_port("/dev/ttyUSB0") as connection:
    device_list = connection.detect_devices()
    #homing the actuator
    device = device_list[0]
    axis = device.get_axis(1)
    axis.settings.set("maxspeed", 20, Units.VELOCITY_MILLIMETRES_PER_SECOND) #set to gentle maximum speed, these should not have to be reset from above, but jic
    axis.settings.set("motion.accelonly",2,Units.NATIVE) #set to gentle acceleration
    axis.settings.set("motion.decelonly",2,Units.NATIVE) #set to gentle deceleration
    axis.home()

# send email
os.system('python3.9 /home/minor/Desktop/Alert_user.py')

cleanup()
