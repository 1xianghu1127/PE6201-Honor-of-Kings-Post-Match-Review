$ErrorActionPreference = "Stop"

$secureKey = Read-Host "Enter your OpenRouter API Key (input hidden)" -AsSecureString
$keyPointer = [IntPtr]::Zero
$plainKey = $null
$exitCode = 1

try {
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw "OpenRouter API Key cannot be empty."
    }

    $env:OPENROUTER_API_KEY = $plainKey
    $pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw "Virtual environment not found. Create .venv and install requirements first."
    }

    & $pythonPath -m streamlit run (Join-Path $PSScriptRoot "app.py")
    $exitCode = $LASTEXITCODE
}
finally {
    Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
    $plainKey = $null
    if ($keyPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
}

exit $exitCode
