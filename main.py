import dht
import network
import time
import urequests
from machine import Pin,I2C,ADC
import ujson
from i2c_lcd import I2cLcd
import _thread

AddressOfLcd = 0x27
i2c = I2C(scl=Pin(22), sda=Pin(21), freq=400000)
lcd = I2cLcd(i2c,AddressOfLcd, 2,16)

sensor = dht.DHT22(Pin(13))

dryDevice = Pin(19, Pin.OUT)
fanDevice = Pin(18,Pin.OUT)
speaker = Pin(23,Pin.OUT)
flame_sensor_pin = 32
adc = ADC(Pin(flame_sensor_pin))
adc.width(ADC.WIDTH_10BIT) 
adc.atten(ADC.ATTN_11DB)

firebase_pushing_data = False
firebase_lock = _thread.allocate_lock()

def read_flame_sensor():
    return adc.read()


dryDevice.value(0)
fanDevice.value(0)
speaker.value(0)

setTemperature = '70'

def read_sensor():
    sensor.measure()
    temperature = sensor.temperature()
    humidity = sensor.humidity()
    return temperature, humidity


def push_to_firebase(url, path, data):
    global firebase_lock
    with firebase_lock:
        try:
            headers = {"Content-Type": "application/json"}
            response = urequests.patch(url + '/' + path + '.json', headers=headers, data=ujson.dumps(data))
            print("Firebase Response:", response.text)
        except Exception as e:
            print("Error pushing data to Firebase:", str(e))

# Set up your Wi-Fi connection
def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        wlan.active(True)
        print("CONNECTING...");
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass

ssid = 'TTTT'
password = '20022002'
connect_to_wifi(ssid, password)

def get_firebase_data(url, path):
    try:
        response = urequests.get(url + '/' + path + '.json')
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print("Failed to retrieve data. Status code:", response.status_code)
            return None
    except Exception as e:
        print("An error occurred:", str(e))
        return None

firebase_url = 'https://pbl3-45657-default-rtdb.asia-southeast1.firebasedatabase.app'
firebase_path = 'sensor'

while True:
    temperature, humidity = read_sensor()
    print("sensor" + str(temperature) + " " + str(humidity));
    lcd.move_to(0,0)
    lcd.putstr('Nhiet do '+ str(temperature) + " 'C")
    lcd.move_to(0,1)
    lcd.putstr('Do am '+ str(humidity) + ' %')
    data = get_firebase_data(firebase_url, firebase_path)
    systemData = get_firebase_data(firebase_url, 'system')
    
    flame_reading = read_flame_sensor()
    
    dataSensor = {"warningFlame": False, "dryDevice": False, "dryDevice": False,"temperature": temperature, "humidity": humidity}
    
    
    if not firebase_lock.locked():
        if flame_reading > 1000:
            speaker.value(1)
            dataSensor.update({"warningFlame": True})
            dataSensor.update({"warningFlame": True})
            push_to_firebase(firebase_url,'sensor',dataSensor)
        else:
            speaker.value(0)
            dataSensor.update({"warningFlame": False})
    
        if systemData is not None and flame_reading < 1000:
            setTemperature = systemData.get('tempDry')
            isStartSystem = systemData.get('isStart')
            isAutoSystem = systemData.get('isAuto')
            dataFanDevice = data.get('fanDevice')
            dataDryDevice = data.get('dryDevice')
            
            if isStartSystem:
                if data is not None:
                    if isAutoSystem:
                        fanDevice.value(1)
                        dataSensor.update({"fanDevice": True})
                        if(str(temperature) >= str(setTemperature)):
                            dryDevice.value(0)
                            dataSensor.update({"dryDevice": False})
                        elif (str(temperature) <= str(setTemperature - 1)):
                            dryDevice.value(1)
                            dataSensor.update({"dryDevice": True})
                        push_to_firebase(firebase_url,'sensor',dataSensor)
                           
                        
            else:
                
                if(dataFanDevice):
                    fanDevice.value(1)
                    
                else:
                    fanDevice.value(0)
                    
                
                if(dataDryDevice):
                    dryDevice.value(1)
                    
                else:
                    dryDevice.value(0)
                    
        else:
            fanDevice.value(0)
            dryDevice.value(0)
            dataSensor.update({"fanDevice": False})
            dataSensor.update({"dryDevice": False})