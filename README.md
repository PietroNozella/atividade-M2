# Casa IoT Residencial com ESP32

Projeto acadêmico individual de IoT residencial usando ESP32 no Wokwi, MicroPython, MQTT, Node-RED, dashboard, página web embarcada, Google Sheets e envio de e-mail.

## Arquivos

- `main.py`: firmware MicroPython do ESP32.
- `ssd1306.py`: driver local do display OLED SSD1306.
- `diagram.json`: circuito do Wokwi.
- `wokwi.toml`: configuração da simulação.
- `node-red-flow.json`: fluxo importável no Node-RED.
- `docs/documentacao.md`: documentação acadêmica.
- `config.example.py`: exemplo opcional para sobrescrever Wi-Fi, MQTT e fuso horário.

## Hardware simulado

Sensores:

- DHT22: temperatura e umidade no GPIO 27.
- LDR: luminosidade no GPIO 34.
- PIR: presença no GPIO 13.
- Potenciômetro: simulação de gás no GPIO 35.

Atuadores:

- LED sala no GPIO 25.
- LED quarto no GPIO 26.
- Servo do portão no GPIO 18.
- Buzzer do alarme no GPIO 19.
- OLED SSD1306 em I2C, SDA 21 e SCL 22.

## Como executar no Wokwi

1. Abra a pasta do projeto no Wokwi.
2. Inicie a simulação.
3. Aguarde o serial mostrar o IP do ESP32.
4. Use a página web em `http://IP_DO_ESP32`.
5. Altere os sensores no Wokwi para ver publicações MQTT, OLED e alertas.

O `wokwi.toml` aponta para o firmware MicroPython local em `ESP32_GENERIC-20251209-v1.27.0.bin`, formato esperado pela extensão do Wokwi no Cursor.

## Como executar no Cursor

Use `mpremote` na mesma versão do firmware MicroPython:

```powershell
python -m pip install --force-reinstall mpremote==1.27.0
```

1. Pare e inicie novamente o simulador pela extensão do Wokwi, para ele carregar o `wokwi.toml`.
2. Aguarde o terminal do Wokwi mostrar `>>>`.
3. Em um terminal PowerShell, envie os arquivos para o MicroPython do simulador e inicie o projeto:

```powershell
.\upload-cursor.ps1
```

4. Acesse a página local pelo navegador em `http://localhost:8180`.

Se aparecer `TransportError: could not enter raw repl`, clique no terminal do Wokwi, pressione `Ctrl + C` para parar o programa e depois `Ctrl + A` para entrar no raw REPL. Volte ao terminal PowerShell e rode `.\upload-cursor.ps1` novamente. Depois do upload, pare e inicie novamente a simulação Wokwi para executar o `main.py`.

No Cursor/VS Code, o simulador inicia apenas o firmware MicroPython. Por isso, sempre que reiniciar a simulação, rode `.\upload-cursor.ps1` novamente para enviar os arquivos e iniciar o `main.py`.

## MQTT

Broker configurado: `broker.hivemq.com`, porta `1883`.

Se quiser usar outro broker, copie `config.example.py` para `config.py` e ajuste os valores. Evite colocar senhas reais em arquivos compartilhados.

Tópicos de sensores:

- `casa/sensores/status`
- `casa/sensores/temperatura`
- `casa/sensores/umidade`
- `casa/sensores/luminosidade`
- `casa/sensores/presenca`
- `casa/sensores/gas`

Tópicos de comando:

- `casa/atuadores/luz_sala/set`
- `casa/atuadores/luz_quarto/set`
- `casa/atuadores/portao/set`
- `casa/atuadores/alarme/set`

Tópicos de estado:

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
3. O node `Google Sheets - configurar URL do Apps Script` já está apontando para a URL informada e envia a chave `meteoro`.
4. Configure o node `Enviar e-mail Gmail` no painel de credenciais do Node-RED:
   - servidor: `smtp.gmail.com`
   - porta: `465`
   - usuário: e-mail remetente
   - senha: senha de app do Gmail
5. Abra o dashboard do Node-RED.

O arquivo `docs/google-apps-script.js` contém um exemplo de `doPost` para receber os dados do Node-RED e gravar na planilha.
O destinatário do alerta está configurado como `nozellasoneto@gmail.com`.

O fluxo:

- exibe sensores em tempo real;
- controla os quatro atuadores por MQTT;
- registra o status no Google Sheets a cada 2 horas;
- registra alertas imediatamente;
- envia e-mail quando recebe alerta no tópico `casa/alertas`;
- envia relatório diário por e-mail às 08:53.

## Alertas

O ESP32 publica alerta quando:

- temperatura for maior ou igual a 35 graus;
- gás for maior ou igual a 70%;
- houver presença com alarme ligado.

Para evitar repetição excessiva, o mesmo ciclo publica alertas com intervalo mínimo de 60 segundos.
