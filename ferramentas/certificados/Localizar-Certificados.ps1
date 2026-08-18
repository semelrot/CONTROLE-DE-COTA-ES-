<#
.SYNOPSIS
    Localiza PDFs que sao certificados de qualidade de material em uma arvore
    de diretorios (ex.: Y:\) e gera um CSV classificado.

.DESCRIPTION
    Versao sem dependencias, para rodar em qualquer Windows com PowerShell 5+.
    Classifica pelo NOME DO ARQUIVO e pelo CAMINHO DA PASTA -- nao abre os PDFs.
    Para tambem ler o conteudo (analise quimica, corrida, propriedades
    mecanicas), use localizar_certificados.py, que e mais preciso.

.EXAMPLE
    .\Localizar-Certificados.ps1 -Raiz "Y:\" -Saida "C:\temp\certificados.csv"

.EXAMPLE
    # so o que tem alta confianca, e ja abre no Excel
    .\Localizar-Certificados.ps1 -Raiz "Y:\" -Minimo CERTIFICADO -Abrir
#>
[CmdletBinding()]
param(
    [string]$Raiz = 'Y:\',
    [string]$Saida = "$env:USERPROFILE\Desktop\certificados_encontrados.csv",
    [ValidateSet('CERTIFICADO', 'PROVAVEL', 'REVISAR', 'NAO')]
    [string]$Minimo = 'REVISAR',
    [int]$Profundidade = 0,
    [string[]]$Ignorar = @('$RECYCLE.BIN', 'System Volume Information', 'temp', 'tmp'),
    [switch]$Abrir
)

$ErrorActionPreference = 'Continue'

# Peso alto: praticamente define o documento.
$TermosFortes = @(
    @{ p = 'certificado\W+de\W+qualidade';        w = 6; x = $true },
    @{ p = 'certificado\W+de\W+materia\W*prima';  w = 6; x = $true },
    @{ p = 'certificado\W+de\W+material';         w = 6; x = $true },
    @{ p = 'certificado\W+de\W+rastreabilidade';  w = 5; x = $true },
    @{ p = 'certificado\W+de\W+ensaio';           w = 5; x = $true },
    @{ p = 'certificado\W+de\W+inspecao';         w = 5; x = $false },
    @{ p = 'certificado\W+de\W+analise';          w = 4; x = $false },
    @{ p = 'certificado\W+de\W+conformidade';     w = 4; x = $false },
    @{ p = 'certificado\W+do\W+fabricante';       w = 4; x = $false },
    @{ p = 'mill\W+test\W+certificate';           w = 6; x = $true },
    @{ p = 'material\W+test\W+report';            w = 6; x = $true },
    @{ p = 'material\W+certificate';              w = 5; x = $true },
    @{ p = 'inspection\W+certificate';            w = 5; x = $false },
    @{ p = 'quality\W+certificate';               w = 5; x = $false },
    @{ p = 'en\W*10204';                          w = 6; x = $true },
    @{ p = 'laudo\W+de\W+ensaio';                 w = 4; x = $true },
    @{ p = 'laudo\W+(de\W+analise|tecnico)';      w = 3; x = $false },
    @{ p = '\bmtc\b';                             w = 3; x = $true },
    @{ p = '\bmtr\b';                             w = 3; x = $true },
    @{ p = '\bcqm\b';                             w = 3; x = $true },
    @{ p = '\bcq\b';                              w = 2; x = $false }
)

# Tipico de certificado de material, porem nao exclusivo.
$TermosApoio = @(
    @{ p = 'analise\W+quimica';        w = 4 },
    @{ p = 'composicao\W+quimica';     w = 4 },
    @{ p = 'propriedades\W+mecanicas'; w = 3 },
    @{ p = 'ensaio\W+de\W+tracao';     w = 3 },
    @{ p = 'numero\W+de\W+corrida';    w = 3 },
    @{ p = '\bcorrida\b';              w = 2 },
    @{ p = 'heat\W*(number|no)';       w = 3 },
    @{ p = 'rastreabilidade';          w = 2 },
    @{ p = '\bcharpy\b';               w = 3 },
    @{ p = 'dureza';                   w = 2 },
    @{ p = 'astm\W*a?\d';              w = 2 },
    @{ p = 'abnt\W+nbr';               w = 2 },
    @{ p = 'aisi\W*\d';                w = 2 },
    @{ p = 'sae\W*\d';                 w = 2 },
    @{ p = 'din\W*\d';                 w = 2 },
    @{ p = 'siderurgic';               w = 2 },
    @{ p = 'tratamento\W+termico';     w = 2 },
    @{ p = '\blote\b';                 w = 1 },
    @{ p = '\bbitola\b';               w = 1 }
)

# Vetos: caracterizam outro tipo de documento. Derrubam para NAO, a menos que
# haja termo exclusivo de material.
$Vetos = @(
    'nota\W+fiscal', '\bdanfe\b', '\bboleto\b', '\bfispq\b',
    'ficha\W+de\W+informacoes\W+de\W+seguranca', 'iso\W*9001', 'iso\W*14001',
    'certificado\W+digital', 'certificado\W+de\W+(participacao|conclusao)',
    '\bcurriculo\b', 'certidao\W+negativa', '\bcnd\b',
    'manual\W+(de\W+)?(instrucoes|do\W+usuario|operacao)', '\bcatalogo\b',
    'contrato\W+social', 'conhecimento\W+de\W+transporte',
    'proposta\W+comercial', '\bromaneio\b', '\bcotacao\b', '\borcamento\b'
)

function Normalizar {
    param([string]$Texto)
    if ([string]::IsNullOrWhiteSpace($Texto)) { return '' }
    # Remove acentos via decomposicao Unicode.
    $d = $Texto.Normalize([Text.NormalizationForm]::FormD)
    $sb = New-Object Text.StringBuilder
    foreach ($ch in $d.ToCharArray()) {
        if ([Globalization.CharUnicodeInfo]::GetUnicodeCategory($ch) -ne
            [Globalization.UnicodeCategory]::NonSpacingMark) { [void]$sb.Append($ch) }
    }
    # "_" e caractere de palavra no regex: viraria barreira em \b e \W+.
    $r = $sb.ToString().ToLowerInvariant().Replace('_', ' ')
    return ($r -replace '\s+', ' ')
}

function Classificar {
    param([string]$Nome, [string]$Pasta)

    $nNome = Normalizar $Nome
    $nPasta = Normalizar $Pasta
    $forte = 0.0; $apoio = 0.0; $neg = 0.0
    $termos = New-Object Collections.Generic.HashSet[string]
    $exclusivo = $false; $veto = $false

    # Nome do arquivo pesa mais que o caminho da pasta.
    foreach ($alvo in @(@{ t = $nNome; m = 2.0 }, @{ t = $nPasta; m = 1.5 })) {
        if (-not $alvo.t) { continue }
        foreach ($termo in $TermosFortes) {
            if ($alvo.t -match $termo.p) {
                $forte += $termo.w * $alvo.m
                [void]$termos.Add($termo.p)
                if ($termo.x) { $exclusivo = $true }
            }
        }
        foreach ($termo in $TermosApoio) {
            if ($alvo.t -match $termo.p) {
                $apoio += $termo.w * $alvo.m
                [void]$termos.Add($termo.p)
            }
        }
        foreach ($v in $Vetos) {
            if ($alvo.t -match $v) { $neg += 3 * $alvo.m; $veto = $true }
        }
    }

    $pesoNeg = if ($forte -lt 4) { $neg } else { $neg * 0.3 }
    $score = $forte + $apoio - $pesoNeg

    $classe =
        if ($forte -ge 8) { 'CERTIFICADO' }
        elseif ($forte -ge 4 -and $apoio -ge 3) { 'CERTIFICADO' }
        elseif ($forte -ge 4) { 'PROVAVEL' }
        elseif ($forte -ge 2 -and $apoio -ge 4) { 'PROVAVEL' }
        elseif ($apoio -ge 8) { 'PROVAVEL' }
        elseif ($forte -ge 2 -or $apoio -ge 4) { 'REVISAR' }
        else { 'NAO' }

    if ($veto -and -not $exclusivo -and $apoio -lt 4) { $classe = 'NAO' }

    return [pscustomobject]@{
        classificacao = $classe
        score         = [math]::Round($score, 1)
        score_forte   = [math]::Round($forte, 1)
        score_apoio   = [math]::Round($apoio, 1)
        termos        = (($termos | ForEach-Object { $_ -replace '\\W[*+?]?', ' ' -replace '\\b|\\d|[()?*+]|\[[^\]]*\]', '' }) -join '; ')
    }
}

if (-not (Test-Path -LiteralPath $Raiz)) {
    Write-Error "Caminho nao encontrado ou inacessivel: $Raiz`nVerifique se o drive esta mapeado e se voce tem permissao."
    exit 1
}

Write-Host "Varrendo $Raiz ..." -ForegroundColor Cyan
$inicio = Get-Date

$pdfs = Get-ChildItem -LiteralPath $Raiz -Filter *.pdf -File -Recurse -Force `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $rel = $_.DirectoryName
            -not ($Ignorar | Where-Object { $rel -like "*\$_*" })
        }

Write-Host "$($pdfs.Count) PDFs encontrados. Classificando..." -ForegroundColor Cyan

$ordem = @{ CERTIFICADO = 0; PROVAVEL = 1; REVISAR = 2; NAO = 3 }
$corte = $ordem[$Minimo]

$resultados = foreach ($pdf in $pdfs) {
    $pastaRel = $pdf.DirectoryName
    if ($pastaRel.StartsWith($Raiz, 'OrdinalIgnoreCase')) {
        $pastaRel = $pastaRel.Substring($Raiz.TrimEnd('\').Length).TrimStart('\')
    }
    $c = Classificar -Nome $pdf.Name -Pasta $pastaRel
    [pscustomobject]@{
        classificacao    = $c.classificacao
        score            = $c.score
        arquivo          = $pdf.Name
        pasta            = $pastaRel
        caminho_completo = $pdf.FullName
        tamanho_kb       = [math]::Round($pdf.Length / 1KB, 1)
        modificado       = $pdf.LastWriteTime.ToString('yyyy-MM-dd HH:mm')
        termos           = $c.termos
        score_forte      = $c.score_forte
        score_apoio      = $c.score_apoio
        obs              = 'Classificado apenas por nome/pasta (nao abre o PDF)'
    }
}

$filtrados = $resultados |
    Where-Object { $ordem[$_.classificacao] -le $corte } |
    Sort-Object @{ e = { $ordem[$_.classificacao] } }, @{ e = 'score'; Descending = $true }, arquivo

$filtrados | Export-Csv -LiteralPath $Saida -NoTypeInformation -Delimiter ';' -Encoding UTF8

Write-Host "`nResumo:" -ForegroundColor Green
$resultados | Group-Object classificacao |
    Sort-Object @{ e = { $ordem[$_.Name] } } |
    ForEach-Object { Write-Host ("  {0,-12} {1}" -f $_.Name, $_.Count) }

$seg = [math]::Round(((Get-Date) - $inicio).TotalSeconds, 1)
Write-Host "`n$($filtrados.Count) linhas gravadas em $Saida ($seg s)" -ForegroundColor Green

if ($Abrir) { Invoke-Item -LiteralPath $Saida }
