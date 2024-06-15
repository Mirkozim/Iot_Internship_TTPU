#================================================================================
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import grpc
import cyberdog_app_pb2
import cyberdog_app_pb2_grpc

#================================================================================
# Define the MQTT broker details
broker_address = "mqtt.iotserver.uz"
port = 1883
mqtt_user = "userTTPU"
mqtt_pass = "mqttpass"
listen_topic = "ttpu/cyber_listen"
status_topic = "ttpu/cyber_status"

# Connection status flag for MQTT
mqtt_connected = False 

# Cyberdog connection flag
cyberdog_connected = False
cyberdog_channel = None

class Vector3:
    x: float = 0
    y: float = 0
    z: float = 0

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z
        pass


MAX_SPEED = 16

stub = None
cyberdog_ip = "localhost"  # Write Your Cyberdog IP Here or Input while running
speed_lv = 1
linear = Vector3(0, 0, 0)
angular = Vector3(0, 0, 0)

# def check_cyberdog_connection():
#     return False

#================================================================================

#------------------------------------------------------------------
# Publish Cyberdog Status
def publish_cyberdog_status(msg):
    global mqttClient
    global mqtt_connected

    if mqtt_connected == False:
        return
    
    mqttClient.publish()

#------------------------------------------------------------------
# Connect to cyberdog
def connect_cyberdog():

    global stub
    global cyberdog_ip

    global cyberdog_connected
    global cyberdog_channel

    if (cyberdog_connected == True):
        return True

    try:
        cyberdog_channel = grpc.insecure_channel(str(cyberdog_ip) + ':50051')
        print("Wait connect")
    except Exception as e:
        print("error cyberdog channel: "+ str(e))
        return False
    
    try:
        grpc.channel_ready_future(cyberdog_channel).result(timeout=10)
    except grpc.FutureTimeoutError:
        print("Connect error, Timeout")
        cyberdog_channel.close()
        cyberdog_connected = False
        return False
    except Exception as e:
        print("Channel Connect Error: " + str(e))
        cyberdog_channel.close()
        cyberdog_connected = False
        return False

    try:
        stub = cyberdog_app_pb2_grpc.CyberdogAppStub(cyberdog_channel)
    except Exception as e:
        print("Stub connect error: " + str(e))
        cyberdog_channel.close()
        cyberdog_connected = False
        return False

    print("CyberDog connected and Ready")
    cyberdog_connected = True

    return True

#------------------------------------------------------------------
# Stand UP
def stand_up_ready_to_walk():
    global stub
    global cyberdog_connected
    global cyberdog_channel

    if (cyberdog_connected == False or cyberdog_channel == None):
        return False
    
    try:

        # Stand up
        response = stub.setMode(
            cyberdog_app_pb2.CheckoutMode_request(
                next_mode=cyberdog_app_pb2.ModeStamped(
                    header=cyberdog_app_pb2.Header(
                        stamp=cyberdog_app_pb2.Timestamp(
                            sec=0,      # seem not need
                            nanosec=0   # seem not need
                        ),
                        frame_id=""     # seem not need
                    ),
                    mode=cyberdog_app_pb2.Mode(
                        control_mode=cyberdog_app_pb2.CheckoutMode_request.MANUAL,
                        mode_type=0     # seem not need
                    )),
                timeout=10))
        succeed_state = False
        for resp in response:
            succeed_state = resp.succeed
            print('Execute Stand up, result:' + str(succeed_state))

        # Change gait to walk
        response = stub.setPattern(
            cyberdog_app_pb2.CheckoutPattern_request(
                patternstamped=cyberdog_app_pb2.PatternStamped(
                    header=cyberdog_app_pb2.Header(
                        stamp=cyberdog_app_pb2.Timestamp(
                            sec=0,      # seem not need
                            nanosec=0   # seem not need
                        ),
                        frame_id=""     # seem not need
                    ),
                    pattern=cyberdog_app_pb2.Pattern(
                        gait_pattern=cyberdog_app_pb2.Pattern.GAIT_TROT
                    )
                ),
                timeout=10
            )
        )
        for resp in response:
            succeed_state = resp.succeed
            print('Change gait to walk, result:' + str(succeed_state))
        return True

    except Exception as e:
        print("Error while Standing UP: " + str(e))
        cyberdog_connected = False
        cyberdog_channel.close()
        return False
    
#------------------------------------------------------------------
# Get Down
def get_down():
    global stub
    global cyberdog_connected
    global cyberdog_channel

    if (cyberdog_connected == False or cyberdog_channel == None):
        return False
    
    try:
        # Get Down
        response = stub.setMode(
            cyberdog_app_pb2.CheckoutMode_request(
                next_mode=cyberdog_app_pb2.ModeStamped(
                    header=cyberdog_app_pb2.Header(
                        stamp=cyberdog_app_pb2.Timestamp(
                            sec=0,      # seem not need
                            nanosec=0   # seem not need
                        ),
                        frame_id=""     # seem not need
                    ),
                    mode=cyberdog_app_pb2.Mode(
                        control_mode=cyberdog_app_pb2.CheckoutMode_request.DEFAULT,
                        mode_type=0     # seem not need
                    )),
                timeout=10))
        for resp in response:
            succeed_state = resp.succeed
            print('Execute Get down, result:' + str(succeed_state))
        return True

    except Exception as e:
        print("Error while Getting DOWN: " + str(e))
        cyberdog_connected = False
        cyberdog_channel.close()
        return False


#------------------------------------------------------------------
# 


#================================================================================
# Define the callbacks
#------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    global mqtt_connected

    if rc == 0:
        mqtt_connected = True

        print("Connected with result code " + str(rc))
        # Subscribe to the topic once connected
        client.subscribe(listen_topic)

        # Get the current date and time
        now = datetime.now()

        # Format the datetime string as "HH:min:sec; year/month/day"
        formatted_datetime = now.strftime("%H:%M:%S; %Y/%m/%d")
        # Publish a message once connected
        client.publish(status_topic, "Alive: " + str(formatted_datetime))

    else:
        mqtt_connected = False
        print("Connection failed with result code " + str(rc))

#------------------------------------------------------------------
def on_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print("Disconnected with result code " + str(rc))

#------------------------------------------------------------------
# function to receive message from subscribed topic
def on_message(client, userdata, msg):
    print("Message received: " + msg.topic + " -> " + msg.payload.decode())
    # check the topic name and command of the message
    # if correct, execute the requested command, publish the result, and exit
    topic = str(msg.topic)
    payload = str(msg.payload.decode())

    # if (payload == "U"):
    #     stand_up_ready_to_walk()

    # elif (payload == "D"):
    #     get_down()

#------------------------------------------------------------------
def on_publish(client, userdata, mid):
    print("Message published: " + str(mid))





#================================================================================
if __name__ == '__main__':

    # global mqtt_connected
    # global cyberdog_connected
    # global cyberdog_ip

    # global cyberdog_channel

    # Define the MQTT client
    mqttClient = mqtt.Client("CyberDogClient")

    mqttClient.username_pw_set(mqtt_user, mqtt_pass);

    # Assign the callbacks
    mqttClient.on_connect = on_connect
    mqttClient.on_disconnect = on_disconnect
    mqttClient.on_message = on_message
    mqttClient.on_publish = on_publish

    # keep the mqtt connection alive
    try:
        while True:

            # check mqtt  connection
            if mqtt_connected == False:
                # mqtt not connected, try again
                print("Attempting to connect to the MQTT broker...")
                try:
                    mqttClient.connect(broker_address, port, 3)
                    # Start the loop to process callback
                    mqttClient.loop_forever()

                except Exception as e:
                    print("MQTT Connection failed: ", e)
                    time.sleep(5)
            
            # else:
                
                # mqtt connected
                
                # check the connection to cyberdog gPRC service
                # cyberdog_connected = check_cyberdog_connection()

                # connect to cyberdog gPRC service (if not connected yet)
                # if (cyberdog_connected == False):
                #     # try to connect to cyberdog
                #     connect_cyberdog()
                
                # if not connected gPRC:
                    # publish error message to "ttpu/cyber_status"
                # else, if success gPRC service:
                    # publish success message to "ttpu/cyber_status"

            time.sleep(0.5)
            
            
            
            # if not connected yet
                # connect to mqtt (if not connected yet)

                # if connect success:
                    # subsribe to the topic "ttpu/cyber_listen"
                    # publish "alive" message to the topic "ttpu/cyber_status"


            # if mqtt connected:

                # check the connection to cyberdog gPRC service
                # connect to cyberdog gPRC service (if not connected yet)
                
                # if not connected gPRC:
                    # publish error message to "ttpu/cyber_status"
                # else, if success gPRC service:
                    # publish success message to "ttpu/cyber_status"

            # if not success mqtt:
                # wait sometime and continue
    
    except KeyboardInterrupt:
        # Stop the loop and disconnect
        mqttClient.loop_stop()
        mqttClient.disconnect()
        if (cyberdog_channel):
            cyberdog_channel.close()
        print("Disconnected from MQTT broker")
        print("Exiting the program")
