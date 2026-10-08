import network
import time
from machine import Pin
import dht
from umqtt.simple import MQTTClient
import json

# 1. Configurações dos Pinos (Sensor e Atuador)
sensor = dht.DHT22(Pin(15))
atuador = Pin(14, Pin.OUT)  # LED ou Relé conectado no GPIO 14
led_wifi = Pin(2, Pin.OUT)  # LED interno para status do WiFi

# 2. Configurações de Tópicos MQTT (Mantenha o prefixo único do seu projeto)
MQTT_BROKER     = "broker.emqx.io"
MQTT_CLIENT_ID  = "esp32_wokwi_dht22_prod"
TOPICO_TELEMETRIA = "dashboard/iot/telemetria"
TOPICO_COMANDO    = "dashboard/iot/telemetria/cmd"  # Tópico para o atuador

# 3. Função Callback: Executada sempre que o Streamlit enviar um comando MQTT
def receber_comando(topico, msg):
    comando = msg.decode("utf-8")
    print(f"Comando recebido no tópico {topico.decode()}: {comando}")
    
    if comando == "LIGAR":
        atuador.value(1)  # Liga o LED/Relé
        print("Atuador LIGADO")
    elif comando == "DESLIGAR":
        atuador.value(0)  # Desliga o LED/Relé
        print("Atuador DESLIGADO")

# 4. Conectando ao Wi-Fi virtual do Wokwi
print("Conectando ao Wi-Fi...", end="")
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('Wokwi-GUEST', '')
while not sta_if.isconnected():
    print(".", end="")
    time.sleep(0.5)
print(" Conectado!")
led_wifi.value(1)

# 5. Conectando ao Broker e Assinando o Tópico de Comandos
print("Conectando ao Broker MQTT...")
client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=1883)
client.set_callback(receber_comando)  # Define a função de escuta
client.connect()
client.subscribe(TOPICO_COMANDO)      # ESP32 se inscreve para ouvir comandos
print(f"Inscrito com sucesso no tópico: {TOPICO_COMANDO}")

# 6. Loop Principal
ultimo_envio = 0
while True:
    try:
        # Verifica se há novas mensagens/comandos vindos do Streamlit (Não bloqueante)
        client.check_msg()
        
        # Envia a telemetria do sensor a cada 5 segundos sem travar a escuta de comandos
        agora = time.time()
        if agora - ultimo_envio >= 5:
            sensor.measure()
            payload = json.dumps({
                "temperatura": sensor.temperature(),
                "umidade": sensor.humidity()
            })
            print(f"Enviando Telemetria: {payload}")
            client.publish(TOPICO_TELEMETRIA, payload)
            ultimo_envio = agora
            
    except Exception as e:
        print("Erro no loop:", e)
        time.sleep(1)