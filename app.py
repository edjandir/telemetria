import streamlit as st
import paho.mqtt.client as mqtt
import json
import sqlite3
import pandas as pd
import time

# Configurações do Broker MQTT
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "dashboard/iot/ifsc-tub"   # Use o mesmo tópico do Wokwi
DB_NAME = "dados_iot.db"

st.set_page_config(page_title="Dashboard IoT com SQLite", layout="wide")
st.title("🗄️ Dashboard IoT: MQTT Subscriber + Banco SQLite")

# 1. Função para inicializar o banco de dados SQLite local
def inicializar_banco():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Cria a tabela caso ela não exista
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

# Inicializa o banco ao rodar o app
inicializar_banco()

# 2. Callback de recebimento de mensagens do MQTT (Salva direto no SQLite)
def quando_receber_mensagem(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        dados = json.loads(payload)
        
        temp = dados.get("temperatura")
        umi = dados.get("umidade")
        
        # Salva no banco de dados SQLite local
        if temp is not None and umi is not None:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO leituras (temperatura, umidade) VALUES (?, ?)", 
                (temp, umi)
            )
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"Erro ao processar e salvar mensagem: {e}")

# 3. Mantém a conexão MQTT persistente no servidor
@st.cache_resource
def iniciar_assinante_mqtt():
    cliente = mqtt.Client()
    cliente.on_message = quando_receber_mensagem
    cliente.connect(MQTT_BROKER, MQTT_PORT, 60)
    cliente.subscribe(MQTT_TOPIC)
    cliente.loop_start()
    return cliente

# Ativa o escutador MQTT em segundo plano
iniciar_assinante_mqtt()

# 4. Função para buscar os dados do SQLite e converter para Pandas DataFrame
def buscar_dados():
    conn = sqlite3.connect(DB_NAME)
    # Busca apenas as últimas 50 leituras para o gráfico ficar limpo
    df = pd.read_sql_query(
        "SELECT datetime(timestamp, 'localtime') as hora, temperatura, umidade FROM leituras ORDER BY id DESC LIMIT 50", 
        conn
    )
    conn.close()
    # Inverte o DataFrame para que o gráfico mostre a ordem cronológica correta (da esquerda para a direita)
    return df.iloc[::-1]

# 5. Interface Gráfica do Streamlit
espaco_metricas = st.empty()
espaco_grafico = st.empty()

# Busca os dados atuais do banco
df_dados = buscar_dados()

if not df_dados.empty:
    # Pega o último registro inserido
    ultimo_registro = df_dados.iloc[-1]
    
    with espaco_metricas.container():
        c1, c2 = st.columns(2)
        c1.metric("🌡️ Temperatura (SQLite)", f"{ultimo_registro['temperatura']} °C")
        c2.metric("💧 Umidade (SQLite)", f"{ultimo_registro['umidade']} %")
        
    with espaco_grafico.container():
        st.subheader("📊 Histórico Gravado no SQLite (Últimas 50 leituras)")
        st.line_chart(df_dados.set_index("hora")[["temperatura", "umidade"]])
else:
    st.info("⏳ Aguardando mensagens do ESP32 para alimentar o banco SQLite...")

# 6. Botão extra para limpar o histórico do banco, se necessário
if st.sidebar.button("🧹 Limpar Banco de Dados"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leituras")
    conn.commit()
    conn.close()
    st.rerun()

# Atualiza a interface a cada 2 segundos para checar se o MQTT inseriu novos dados no arquivo
time.sleep(2)
st.rerun()
