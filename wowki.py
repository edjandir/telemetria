import network
import time
from machine import Pin
import dht
from umqtt.simple import MQTTClient
import json

# 1. Configurações do Sensor DHT22 e LED indicador
sensor = dht.DHT22(Pin(15))
led = Pin(2, Pin.OUT) # LED onboard do ESP32 para dar feedback visual

# 2. Configuração do Wi-Fi do simulador Wokwi
print("Conectando ao Wi-Fi virtual do Wokwi...", end="")
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('Wokwi-GUEST', '') # Rede padrão obrigatória do Wokwi
while not sta_if.isconnected():
    print(".", end="")
    time.sleep(0.5)
print(" Conectado com sucesso!")

# 3. Configurações do Broker MQTT (EMQX Público)
MQTT_BROKER    = "broker.emqx.io"
MQTT_CLIENT_ID = "esp32_wokwi_dht22_prod"

MQTT_TOPIC     = "dashboard/iot/ifsc-tub" 

print("Conectando ao Broker MQTT:", MQTT_BROKER)
try:
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=1883)
    client.connect()
    print("Conectado ao Broker MQTT com sucesso!")
except Exception as e:
    print("Erro ao conectar no Broker:", e)

# 4. Loop de leitura e envio de dados
while True:
    try:
        # Pisca o LED indicando que começou uma nova leitura
        led.value(1)
        
        # Faz a leitura do sensor virtual
        sensor.measure()
        temperatura = sensor.temperature()
        umidade = sensor.humidity()
        
        # Cria a estrutura do dicionário/JSON exatamente como o Streamlit espera
        payload_dict = {
            "temperatura": temperatura,
            "umidade": umidade
        }
        payload_json = json.dumps(payload_dict)
        
        # Publica no broker MQTT
        print(f"Publicando no tópico [{MQTT_TOPIC}]: {payload_json}")
        client.publish(MQTT_TOPIC, payload_json)
        
        led.value(0)
    except Exception as e:
        print("Erro ao ler sensor ou enviar via MQTT:", e)
        
    # Envia dados a cada 5 segundos
    time.sleep(5)