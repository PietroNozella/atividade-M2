# Documentacao Academica - Casa IoT Residencial

## 1. Objetivo

O projeto implementa uma residencia inteligente simulada no Wokwi com ESP32 programado em MicroPython. A solucao integra sensores, atuadores, display OLED, MQTT, dashboard Node-RED, registro em Google Sheets e envio de e-mail em situacoes de alerta.

## 2. Componentes

### Sensores

| Sensor | Funcao | Pino |
| --- | --- | --- |
| DHT22 | Temperatura e umidade | GPIO 27 |
| LDR | Luminosidade | GPIO 34 |
| PIR | Presenca | GPIO 13 |
| Potenciometro | Simulacao de nivel de gas | GPIO 35 |

### Atuadores

| Atuador | Funcao | Pino |
| --- | --- | --- |
| Modulo rele 1 canal | Luz da sala | GPIO 25 |
| Modulo rele 1 canal | Luz do quarto | GPIO 26 |
| Servo motor | Portao | GPIO 18 |
| Buzzer | Alarme sonoro | GPIO 19 |
| OLED SSD1306 | Painel de status | SDA 21 / SCL 22 |

O OLED atua como painel informativo e nao foi contado como um dos quatro atuadores obrigatorios.

## 3. Funcionamento Geral

O ESP32 executa um loop principal simples:

1. Mantem conexao Wi-Fi.
2. Mantem conexao MQTT com o broker HiveMQ.
3. Sincroniza data e hora por NTP quando possivel.
4. Le os sensores periodicamente.
5. Publica leituras em topicos MQTT individuais e em um topico JSON consolidado.
6. Recebe comandos MQTT para os atuadores.
7. Atualiza o OLED com dados dos sensores, horario e estados dos atuadores.
8. Publica alertas quando alguma condicao de risco e detectada.

## 4. Comunicacao MQTT

O broker usado e `broker.hivemq.com`, porta `1883`.
As configuracoes principais podem ser sobrescritas por um arquivo local `config.py`, tomando como base `config.example.py`.

### Publicacao de sensores

- `casa/sensores/status`: JSON consolidado com sensores, atuadores e IP.
- `casa/sensores/temperatura`: temperatura.
- `casa/sensores/umidade`: umidade.
- `casa/sensores/luminosidade`: luminosidade percentual.
- `casa/sensores/presenca`: `1` quando ha presenca, `0` quando nao ha.
- `casa/sensores/gas`: nivel de gas percentual.

### Comandos dos atuadores

- `casa/atuadores/luz_sala/set`
- `casa/atuadores/luz_quarto/set`
- `casa/atuadores/portao/set`
- `casa/atuadores/alarme/set`

Cada atuador escuta apenas o seu proprio topico. Isso evita que um comando da luz da sala interfira no quarto, portao ou alarme.

### Estados dos atuadores

- `casa/atuadores/luz_sala/status`
- `casa/atuadores/luz_quarto/status`
- `casa/atuadores/portao/status`
- `casa/atuadores/alarme/status`

Sempre que um atuador muda, o ESP32 publica o estado atualizado. Assim, o Node-RED consegue refletir o estado real.

## 5. Dashboard Node-RED

O arquivo `node-red-flow.json` contem:

- gauges para temperatura, umidade, luminosidade e gas;
- indicador textual de presenca;
- switches para controlar luz da sala, luz do quarto, portao e alarme;
- inscricao nos topicos MQTT;
- envio de comandos MQTT para o ESP32.

O dashboard permite acompanhar a residencia em tempo real e controlar os atuadores pelo fluxo MQTT.

## 6. Google Sheets e E-mail

O registro no Google Sheets e feito pelo Node-RED, usando um node HTTP Request apontando para um Web App do Google Apps Script.
O arquivo `docs/google-apps-script.js` traz um exemplo simples de script para publicar como Web App.
Neste projeto, o fluxo exportado ja possui a URL do Apps Script configurada e envia a chave de validacao definida no script.

O fluxo possui dois tipos de registro:

- a cada 2 horas, registra o ultimo status consolidado dos sensores;
- imediatamente ao receber alerta em `casa/alertas`, registra o alerta.

O envio de e-mail tambem e feito no Node-RED. Quando um alerta chega pelo MQTT, o fluxo monta uma mensagem e envia pelo node de e-mail configurado com SMTP. Alem disso, o fluxo envia um relatorio diario as 08:53 com o ultimo status consolidado dos sensores e atuadores.
O destinatario configurado no fluxo e `nozellasoneto@gmail.com`; usuario e senha de app devem ser preenchidos nas credenciais do Node-RED.

## 7. Regras de Alerta

O ESP32 publica alerta quando:

- temperatura for maior ou igual a 35 graus;
- gas for maior ou igual a 70%;
- o sensor PIR detectar presenca enquanto o alarme estiver ligado.

Para evitar excesso de mensagens, ha um intervalo minimo de 60 segundos entre publicacoes de alerta.

## 8. Organizacao do Codigo

O codigo foi dividido em funcoes pequenas:

- conexao Wi-Fi;
- conexao MQTT;
- leitura de sensores;
- controle de atuadores;
- publicacao de estados;
- verificacao de alertas;
- atualizacao do OLED.

Essa organizacao facilita testes incrementais e evita misturar logica de sensores, atuadores e comunicacao.

## 9. Execucao do Projeto

Para executar o projeto no Wokwi/Cursor:

1. Abrir a pasta do projeto no editor.
2. Iniciar a simulacao Wokwi usando o circuito de `diagram.json`.
3. Aguardar o terminal do MicroPython mostrar o prompt `>>>`.
4. Executar `.\upload-cursor.ps1` para enviar `main.py` e `ssd1306.py` ao simulador.
5. Confirmar no terminal que o ESP32 conectou ao Wi-Fi e ao broker MQTT.
6. Importar `node-red-flow.json` no Node-RED.
7. Abrir o dashboard do Node-RED e acompanhar as leituras em tempo real.

Caso seja necessario alterar Wi-Fi, broker MQTT ou fuso horario, o arquivo `config.example.py` pode ser copiado para `config.py` e ajustado localmente.

## 10. Validacao e Evidencias

O funcionamento pode ser validado pelo fluxo completo:

1. Alterar temperatura, luminosidade, gas ou presenca no Wokwi.
2. Verificar a atualizacao dos sensores no OLED e no dashboard Node-RED.
3. Acionar luz da sala, luz do quarto, portao e alarme pelo dashboard.
4. Confirmar que os comandos chegam ao ESP32 via MQTT e que os estados retornam ao Node-RED.
5. Forcar uma regra de alerta, como temperatura maior ou igual a 35 graus, gas maior ou igual a 70% ou presenca com alarme ligado.
6. Verificar o registro no Google Sheets e o envio de e-mail.

As evidencias visuais estao na pasta `docs/prints/`:

- `simulador-rodando.png`: simulacao do ESP32 em execucao.
- `sistema-node-red.png`: fluxo geral no Node-RED.
- `node-red-dashboard.png`: dashboard com sensores e controles.
- `dash-node-red.png`: visualizacao dos dados no dashboard.
- `registro-planilha.png`: dados registrados no Google Sheets.
- `email-enviado.png`: e-mail de alerta/relatorio enviado.

## 11. Conclusao

O projeto atende aos requisitos principais da atividade ao combinar sensoriamento, atuacao, comunicacao MQTT bidirecional, dashboard Node-RED, registro em planilha e notificacao por e-mail. A arquitetura foi mantida simples para priorizar funcionamento no Wokwi e facilitar manutencao.
