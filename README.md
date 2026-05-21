# Casa IoT Residencial com ESP32

Projeto academico individual de IoT residencial usando ESP32 no Wokwi, MicroPython, MQTT, Node-RED, dashboard, pagina web embarcada, Google Sheets e envio de e-mail.

## Arquivos

- `main.py`: firmware MicroPython do ESP32.
- `ssd1306.py`: driver local do display OLED SSD1306.
- `diagram.json`: circuito do Wokwi.
- `wokwi.toml`: configuracao da simulacao.
- `node-red-flow.json`: fluxo importavel no Node-RED.
- `docs/documentacao.md`: documentacao academica.
- `config.example.py`: exemplo opcional para sobrescrever Wi-Fi, MQTT e fuso horario.

## Hardware simulado 

Sensores:

- DHT22: temperatura e umidade no GPIO 27.
- LDR: luminosidade no GPIO 34.
- PIR: presenca no GPIO 13.
- Potenciometro: simulacao de gas no GPIO 35.

Atuadores:

- LED sala no GPIO 25.
- LED quarto no GPIO 26.
- Servo do portao no GPIO 18.
- Buzzer do alarme no GPIO 19.
- OLED SSD1306 em I2C, SDA 21 e SCL 22.

## Como executar no Wokwi

1. Abra a pasta do projeto no Wokwi.
2. Inicie a simulacao.
3. Aguarde o serial mostrar o IP do ESP32.
4. Use a pagina web em `http://IP_DO_ESP32`.
5. Altere os sensores no Wokwi para ver publicacoes MQTT, OLED e alertas.

O `wokwi.toml` aponta para o firmware MicroPython local em `ESP32_GENERIC-20251209-v1.27.0.bin`, formato esperado pela extensao do Wokwi no Cursor.

## Como executar no Cursor

Use `mpremote` na mesma versao do firmware MicroPython:

```powershell
python -m pip install --force-reinstall mpremote==1.27.0
```

1. Pare e inicie novamente o simulador pela extensao do Wokwi, para ele carregar o `wokwi.toml`.
2. Aguarde o terminal do Wokwi mostrar `>>>`.
3. Em um terminal PowerShell, envie os arquivos para o MicroPython do simulador e inicie o projeto:

```powershell
.\upload-cursor.ps1
```

4. Acesse a pagina local pelo navegador em `http://localhost:8180`.

Se aparecer `TransportError: could not enter raw repl`, clique no terminal do Wokwi, pressione `Ctrl + C` para parar o programa e depois `Ctrl + A` para entrar no raw REPL. Volte ao terminal PowerShell e rode `.\upload-cursor.ps1` novamente. Depois do upload, pare e inicie novamente a simulacao Wokwi para executar o `main.py`.

No Cursor/VS Code, o simulador inicia apenas o firmware MicroPython. Por isso, sempre que reiniciar a simulacao, rode `.\upload-cursor.ps1` novamente para enviar os arquivos e iniciar o `main.py`.

## MQTT

Broker configurado: `broker.hivemq.com`, porta `1883`.

Se quiser usar outro broker, copie `config.example.py` para `config.py` e ajuste os valores. Evite colocar senhas reais em arquivos compartilhados.

Topicos de sensores:

- `casa/sensores/status`
- `casa/sensores/temperatura`
- `casa/sensores/umidade`
- `casa/sensores/luminosidade`
- `casa/sensores/presenca`
- `casa/sensores/gas`

Topicos de comando:

- `casa/atuadores/luz_sala/set`
- `casa/atuadores/luz_quarto/set`
- `casa/atuadores/portao/set`
- `casa/atuadores/alarme/set`

Topicos de estado:

- `casa/atuadores/luz_sala/status`
- `casa/atuadores/luz_quarto/status`
- `casa/atuadores/portao/status`
- `casa/atuadores/alarme/status`

Alertas:

- `casa/alertas`

Comandos aceitos: `ON`, `OFF`, `1`, `0`, `LIGAR`, `DESLIGAR`, `ABRIR`, `FECHAR`.

## Node-RED

1. Instale Node-RED com dashboard, MQTT e e-mail.
2. Importe `node-red-flow.json`.
3. O node `Google Sheets - configurar URL do Apps Script` ja esta apontando para a URL informada e envia a chave `meteoro`.
4. Configure o node `Enviar e-mail Gmail` no painel de credenciais do Node-RED:
   - servidor: `smtp.gmail.com`
   - porta: `465`
   - usuario: e-mail remetente
   - senha: senha de app do Gmail
5. Abra o dashboard do Node-RED.

O arquivo `docs/google-apps-script.js` contem um exemplo de `doPost` para receber os dados do Node-RED e gravar na planilha.
O destinatario do alerta esta configurado como `nozellasoneto@gmail.com`.

O fluxo:

- exibe sensores em tempo real;
- controla os quatro atuadores por MQTT;
- registra o status no Google Sheets a cada 2 horas;
- registra alertas imediatamente;
- envia e-mail quando recebe alerta no topico `casa/alertas`.
- envia relatorio diario por e-mail as 08:53.

## Alertas

O ESP32 publica alerta quando:

- temperatura for maior ou igual a 35 graus;
- gas for maior ou igual a 70%;
- houver presenca com alarme ligado.

Para evitar repeticao excessiva, o mesmo ciclo publica alertas com intervalo minimo de 60 segundos.
