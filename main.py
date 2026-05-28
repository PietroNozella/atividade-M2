import time
from machine import ADC, PWM, Pin, SoftI2C, unique_id
import dht
import network
from ubinascii import hexlify

try:
    import ujson as json
except ImportError:
    import json

try:
    import ntptime
except ImportError:
    ntptime = None

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None

try:
    from ssd1306 import SSD1306_I2C
except ImportError:
    SSD1306_I2C = None

try:
    import config
except ImportError:
    config = None


# Wi-Fi padrao do Wokwi.
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_USERNAME = None
MQTT_PASSWORD = None
MQTT_SSL = False
MQTT_CLIENT_ID = b"casa-iot-" + hexlify(unique_id())
UTC_OFFSET_HOURS = -3

TOPICS = {
    "sensor_status": "casa/sensores/status",
    "temperatura": "casa/sensores/temperatura",
    "umidade": "casa/sensores/umidade",
    "luminosidade": "casa/sensores/luminosidade",
    "presenca": "casa/sensores/presenca",
    "gas": "casa/sensores/gas",
    "alertas": "casa/alertas",
    "luz_sala_set": "casa/atuadores/luz_sala/set",
    "luz_quarto_set": "casa/atuadores/luz_quarto/set",
    "portao_set": "casa/atuadores/portao/set",
    "alarme_set": "casa/atuadores/alarme/set",
    "luz_sala_status": "casa/atuadores/luz_sala/status",
    "luz_quarto_status": "casa/atuadores/luz_quarto/status",
    "portao_status": "casa/atuadores/portao/status",
    "alarme_status": "casa/atuadores/alarme/status",
}

# Pinos do circuito em diagram.json.
PIN_DHT = 27
PIN_LDR = 34
PIN_PIR = 13
PIN_GAS = 35
PIN_RELAY_SALA = 25
PIN_RELAY_QUARTO = 26
PIN_SERVO = 18
PIN_BUZZER = 19
PIN_OLED_SDA = 21
PIN_OLED_SCL = 22

PUBLICAR_SENSORES_MS = 5000
ATUALIZAR_OLED_MS = 1000
TENTAR_MQTT_MS = 15000
INTERVALO_ALERTA_MS = 60000
SINCRONIZAR_RELOGIO_MS = 6 * 60 * 60 * 1000
VOLUME_ALARME = 80
LOG_SENSORES = False

if config is not None:
    WIFI_SSID = getattr(config, "WIFI_SSID", WIFI_SSID)
    WIFI_PASSWORD = getattr(config, "WIFI_PASSWORD", WIFI_PASSWORD)
    MQTT_BROKER = getattr(config, "MQTT_BROKER", MQTT_BROKER)
    MQTT_PORT = getattr(config, "MQTT_PORT", MQTT_PORT)
    MQTT_USERNAME = getattr(config, "MQTT_USERNAME", MQTT_USERNAME)
    MQTT_PASSWORD = getattr(config, "MQTT_PASSWORD", MQTT_PASSWORD)
    MQTT_SSL = getattr(config, "MQTT_SSL", MQTT_SSL)
    MQTT_CLIENT_ID = getattr(config, "MQTT_CLIENT_ID", MQTT_CLIENT_ID)
    UTC_OFFSET_HOURS = getattr(config, "UTC_OFFSET_HOURS", UTC_OFFSET_HOURS)

if isinstance(MQTT_CLIENT_ID, str):
    MQTT_CLIENT_ID = MQTT_CLIENT_ID.encode()

UTC_OFFSET_SECONDS = UTC_OFFSET_HOURS * 3600


dht_sensor = dht.DHT22(Pin(PIN_DHT))
ldr = ADC(Pin(PIN_LDR))
gas = ADC(Pin(PIN_GAS))
pir = Pin(PIN_PIR, Pin.IN)
relay_sala = Pin(PIN_RELAY_SALA, Pin.OUT)
relay_quarto = Pin(PIN_RELAY_QUARTO, Pin.OUT)
servo = PWM(Pin(PIN_SERVO))
servo.freq(50)
buzzer = PWM(Pin(PIN_BUZZER))
buzzer.freq(1000)

for adc in (ldr, gas):
    adc.atten(ADC.ATTN_11DB)
    try:
        adc.width(ADC.WIDTH_12BIT)
    except AttributeError:
        pass

oled = None
try:
    if SSD1306_I2C:
        i2c = SoftI2C(scl=Pin(PIN_OLED_SCL), sda=Pin(PIN_OLED_SDA))
        oled = SSD1306_I2C(128, 64, i2c)
except Exception as erro:
    print("OLED indisponivel:", erro)

wifi = network.WLAN(network.STA_IF)
mqtt = None

sensores = {
    "temperatura": 0,
    "umidade": 0,
    "luminosidade": 0,
    "presenca": False,
    "gas": 0,
}

atuadores = {
    "luz_sala": False,
    "luz_quarto": False,
    "portao": "FECHADO",
    "alarme": False,
}

ultimo_envio_sensores = 0
ultima_atualizacao_oled = 0
ultima_tentativa_mqtt = 0
ultimo_alerta = 0
ultima_sincronizacao_relogio = 0
data_hora = "--"


def percentual_adc(adc):
    return round((adc.read() / 4095) * 100, 1)


def duty_pwm(pwm, duty_10bits):
    try:
        pwm.duty(duty_10bits)
    except AttributeError:
        pwm.duty_u16(int((duty_10bits / 1023) * 65535))


def mqtt_bytes(valor):
    if isinstance(valor, bytes):
        return valor
    return str(valor).encode()


def mqtt_texto(valor):
    if isinstance(valor, bytes):
        return valor.decode()
    return str(valor)


def definir_servo(angulo):
    duty = int(26 + (angulo / 180) * 102)
    duty_pwm(servo, duty)


def definir_alarme(ligado):
    atuadores["alarme"] = ligado
    duty_pwm(buzzer, VOLUME_ALARME if ligado else 0)


def aplicar_estado_atuador(nome, valor):
    if nome == "luz_sala":
        atuadores["luz_sala"] = valor
        relay_sala.value(1 if valor else 0)
    elif nome == "luz_quarto":
        atuadores["luz_quarto"] = valor
        relay_quarto.value(1 if valor else 0)
    elif nome == "portao":
        atuadores["portao"] = "ABERTO" if valor else "FECHADO"
        definir_servo(90 if valor else 0)
    elif nome == "alarme":
        definir_alarme(valor)


def normalizar_comando(payload):
    comando = mqtt_texto(payload).strip().upper()
    return comando in ("1", "ON", "TRUE", "LIGAR", "ABRIR", "ABERTO")


def formatar_data_hora(instante):
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        instante[0], instante[1], instante[2], instante[3], instante[4], instante[5]
    )


def agora_local():
    try:
        return time.localtime(time.time() + UTC_OFFSET_SECONDS)
    except Exception:
        return time.localtime()


def atualizar_data_hora():
    global data_hora
    data_hora = formatar_data_hora(agora_local())


def sincronizar_relogio():
    global ultima_sincronizacao_relogio
    if ntptime is None or not wifi.isconnected():
        return

    try:
        ntptime.settime()
        ultima_sincronizacao_relogio = time.ticks_ms()
        atualizar_data_hora()
        print("Relogio sincronizado:", data_hora)
    except Exception as erro:
        print("Falha ao sincronizar relogio:", erro)


def publicar(topic, payload, retain=False):
    global mqtt
    if not mqtt:
        return

    try:
        mqtt.publish(mqtt_bytes(topic), mqtt_bytes(payload), retain)
    except Exception as erro:
        print("Falha ao publicar MQTT:", erro)
        mqtt = None


def publicar_estado_atuador(nome):
    topicos = {
        "luz_sala": TOPICS["luz_sala_status"],
        "luz_quarto": TOPICS["luz_quarto_status"],
        "portao": TOPICS["portao_status"],
        "alarme": TOPICS["alarme_status"],
    }

    valor = atuadores[nome]
    if isinstance(valor, bool):
        valor = "ON" if valor else "OFF"

    publicar(topicos[nome], valor, retain=True)


def publicar_todos_estados():
    for nome in atuadores:
        publicar_estado_atuador(nome)


def ao_receber_mqtt(topic, payload):
    topic = mqtt_texto(topic)
    comandos = {
        TOPICS["luz_sala_set"]: "luz_sala",
        TOPICS["luz_quarto_set"]: "luz_quarto",
        TOPICS["portao_set"]: "portao",
        TOPICS["alarme_set"]: "alarme",
    }

    if topic in comandos:
        nome = comandos[topic]
        aplicar_estado_atuador(nome, normalizar_comando(payload))
        publicar_estado_atuador(nome)


def conectar_wifi():
    wifi.active(True)
    if wifi.isconnected():
        return True

    print("Conectando ao Wi-Fi...")
    wifi.connect(WIFI_SSID, WIFI_PASSWORD)
    inicio = time.ticks_ms()

    while not wifi.isconnected() and time.ticks_diff(time.ticks_ms(), inicio) < 15000:
        time.sleep(0.2)

    if wifi.isconnected():
        print("Wi-Fi conectado:", wifi.ifconfig()[0])
        return True

    print("Wi-Fi nao conectado. Tentando novamente no loop principal.")
    return False


def conectar_mqtt():
    global mqtt, ultima_tentativa_mqtt
    agora = time.ticks_ms()
    if mqtt or time.ticks_diff(agora, ultima_tentativa_mqtt) < TENTAR_MQTT_MS:
        return

    ultima_tentativa_mqtt = agora

    if MQTTClient is None:
        print("Biblioteca umqtt.simple indisponivel")
        return

    if not wifi.isconnected():
        return

    try:
        cliente = MQTTClient(
            MQTT_CLIENT_ID,
            MQTT_BROKER,
            port=MQTT_PORT,
            user=mqtt_bytes(MQTT_USERNAME) if MQTT_USERNAME else None,
            password=mqtt_bytes(MQTT_PASSWORD) if MQTT_PASSWORD else None,
            ssl=MQTT_SSL,
        )
        cliente.set_callback(ao_receber_mqtt)
        cliente.connect()
        for topic in (
            TOPICS["luz_sala_set"],
            TOPICS["luz_quarto_set"],
            TOPICS["portao_set"],
            TOPICS["alarme_set"],
        ):
            cliente.subscribe(mqtt_bytes(topic))
        mqtt = cliente
        print("MQTT conectado:", MQTT_BROKER)
        publicar_todos_estados()
    except Exception as erro:
        mqtt = None
        print("Falha no MQTT:", erro)


def ler_sensores():
    try:
        dht_sensor.measure()
        sensores["temperatura"] = round(dht_sensor.temperature(), 1)
        sensores["umidade"] = round(dht_sensor.humidity(), 1)
    except Exception as erro:
        print("Falha ao ler DHT22:", erro)
        pass

    sensores["luminosidade"] = percentual_adc(ldr)
    sensores["gas"] = percentual_adc(gas)
    sensores["presenca"] = bool(pir.value())


def payload_status():
    return {
        "data_hora": data_hora,
        "sensores": sensores,
        "atuadores": atuadores,
        "ip": wifi.ifconfig()[0] if wifi.isconnected() else "sem-wifi",
    }


def publicar_sensores():
    publicar(TOPICS["temperatura"], sensores["temperatura"])
    publicar(TOPICS["umidade"], sensores["umidade"])
    publicar(TOPICS["luminosidade"], sensores["luminosidade"])
    publicar(TOPICS["presenca"], 1 if sensores["presenca"] else 0)
    publicar(TOPICS["gas"], sensores["gas"])
    publicar(TOPICS["sensor_status"], json.dumps(payload_status()))


def alerta_atual():
    alertas = []
    if sensores["temperatura"] >= 35:
        alertas.append("Temperatura alta")
    if sensores["gas"] >= 70:
        alertas.append("Nivel de gas alto")
    if sensores["presenca"] and atuadores["alarme"]:
        alertas.append("Movimento detectado com alarme ativo")
    return alertas


def verificar_alertas():
    global ultimo_alerta
    alertas = alerta_atual()
    if not alertas:
        return

    agora = time.ticks_ms()
    if time.ticks_diff(agora, ultimo_alerta) < INTERVALO_ALERTA_MS:
        return

    ultimo_alerta = agora
    mensagem = {
        "data_hora": data_hora,
        "alertas": alertas,
        "sensores": sensores,
        "atuadores": atuadores,
    }
    publicar(TOPICS["alertas"], json.dumps(mensagem))
    print("ALERTA:", ", ".join(alertas))


def atualizar_oled():
    if not oled:
        return

    oled.fill(0)
    oled.text("Casa IoT", 0, 0)
    oled.text("T:%sC U:%s%%" % (sensores["temperatura"], sensores["umidade"]), 0, 12)
    oled.text("Luz:%s%% Gas:%s%%" % (sensores["luminosidade"], sensores["gas"]), 0, 24)
    oled.text("PIR:%s" % ("SIM" if sensores["presenca"] else "NAO"), 0, 36)
    oled.text("Sala:%s Q:%s" % (
        "ON" if atuadores["luz_sala"] else "OFF",
        "ON" if atuadores["luz_quarto"] else "OFF",
    ), 0, 48)
    oled.text("%s P:%s" % (data_hora[11:16], atuadores["portao"][:3]), 0, 56)
    oled.show()


def setup():
    print("Iniciando Casa IoT...")
    aplicar_estado_atuador("luz_sala", False)
    aplicar_estado_atuador("luz_quarto", False)
    aplicar_estado_atuador("portao", False)
    aplicar_estado_atuador("alarme", False)
    conectar_wifi()
    sincronizar_relogio()
    conectar_mqtt()
    print("Setup finalizado")


setup()

while True:
    agora = time.ticks_ms()

    if not wifi.isconnected():
        if conectar_wifi():
            sincronizar_relogio()
    elif time.ticks_diff(agora, ultima_sincronizacao_relogio) >= SINCRONIZAR_RELOGIO_MS:
        sincronizar_relogio()

    atualizar_data_hora()
    conectar_mqtt()

    if mqtt:
        try:
            mqtt.check_msg()
        except Exception as erro:
            print("Falha ao ler MQTT:", erro)
            mqtt = None

    if time.ticks_diff(agora, ultimo_envio_sensores) >= PUBLICAR_SENSORES_MS:
        ultimo_envio_sensores = agora
        ler_sensores()
        publicar_sensores()
        verificar_alertas()
        if LOG_SENSORES:
            print("Sensores:", json.dumps(payload_status()))

    if time.ticks_diff(agora, ultima_atualizacao_oled) >= ATUALIZAR_OLED_MS:
        ultima_atualizacao_oled = agora
        atualizar_oled()

    time.sleep(0.05)
