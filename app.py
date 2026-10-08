import streamlit as st
import paho.mqtt.client as mqtt
import json
import sqlite3
import pandas as pd
import time

# Configurações do Broker MQTT (Devem bater exatamente com o ESP32)
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPICO_TELEMETRIA = "dashboard/iot/telemetria"
TOPICO_COMANDO = "dashboard/iot/telemetria/cmd"
DB_NAME = "dados_iot.db"

st.set_page_config(page_title="Dashboard IoT Completo", layout="wide")
st.title("🎛️ Portal IoT Centralizado: Sensores e Atuadores")

# 1. Inicializar Banco SQLite
def inicializar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leituras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperatura REAL,
            umidade REAL
        )
    ''')
    conn.commit()
    conn.close()

inicializar_banco()

# 2. Callback de recebimento (Telemetria ➡️ SQLite)
def quando_receber_mensagem(client, userdata, msg):
    try:
        if msg.topic == TOPICO_TELEMETRIA:
            payload = msg.payload.decode("utf-8")
            dados = json.loads(payload)
            temp = dados.get("temperatura")
            umi = dados.get("umidade")
            
            if temp is not None and umi is not None:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO leituras (temperatura, umidade) VALUES (?, ?)", (temp, umi))
                conn.commit()
                conn.close()
    except Exception as e:
        print(f"Erro ao salvar telemetria: {e}")

# 3. Inicializar Conexão MQTT Persistente
@st.cache_resource
def iniciar_cliente_mqtt():
    cliente = mqtt.Client()
    cliente.on_message = quando_receber_mensagem
    cliente.connect(MQTT_BROKER, MQTT_PORT, 60)
    cliente.subscribe(TOPICO_TELEMETRIA)
    cliente.loop_start()
    return cliente

# Ativa o cliente MQTT
mqtt_client = iniciar_cliente_mqtt()

# 4. Painel de Controle do Atuador (Na barra lateral)
st.sidebar.header("🕹️ Controle de Atuadores")

# Botões para publicar o comando de Ligar ou Desligar diretamente no Broker
if st.sidebar.button("🟢 Ligar Dispositivo (LED/Relé)", use_container_width=True):
    mqtt_client.publish(TOPICO_COMANDO, "LIGAR")
    st.sidebar.success("Comando 'LIGAR' enviado!")

if st.sidebar.button("🔴 Desligar Dispositivo (LED/Relé)", use_container_width=True):
    mqtt_client.publish(TOPICO_COMANDO, "DESLIGAR")
    st.sidebar.error("Comando 'DESLIGAR' enviado!")

# 5. Renderização da Interface de Monitoramento
espaco_metricas = st.empty()
espaco_grafico = st.empty()

def buscar_dados():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT datetime(timestamp, 'localtime') as hora, temperatura, umidade FROM leituras ORDER BY id DESC LIMIT 50", conn)
    conn.close()
    return df.iloc[::-1]

df_dados = buscar_dados()

if not df_dados.empty:
    ultimo_registro = df_dados.iloc[-1]
    with espaco_metricas.container():
        c1, c2 = st.columns(2)
        c1.metric("🌡️ Temperatura Atual", f"{ultimo_registro['temperatura']} °C")
        c2.metric("💧 Umidade Relativa", f"{ultimo_registro['umidade']} %")
        
    with espaco_grafico.container():
        st.subheader("📊 Histórico Gravado no SQLite")
        st.line_chart(df_dados.set_index("hora")[["temperatura", "umidade"]])
else:
    st.info("⏳ Aguardando primeiras telemetrias do ESP32...")

# Atualização automática da tela a cada 1 segundo
time.sleep(1)
st.rerun()
