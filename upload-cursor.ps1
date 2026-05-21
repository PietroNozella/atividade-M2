$porta = 4000
$conexao = Test-NetConnection -ComputerName localhost -Port $porta -InformationLevel Quiet

if (-not $conexao) {
    Write-Host "A porta serial do Wokwi nao esta aberta em localhost:$porta." -ForegroundColor Yellow
    Write-Host "No Cursor, pare e inicie novamente o simulador Wokwi depois de salvar o wokwi.toml." -ForegroundColor Yellow
    Write-Host "Quando o simulador estiver rodando, execute este script novamente." -ForegroundColor Yellow
    exit 1
}

python upload-files-direct.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha ao enviar arquivos." -ForegroundColor Red
    Write-Host "Pare e inicie o simulador Wokwi. Quando aparecer >>>, rode este script novamente." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "Arquivos enviados." -ForegroundColor Green
Write-Host "main.py iniciado no simulador." -ForegroundColor Green
