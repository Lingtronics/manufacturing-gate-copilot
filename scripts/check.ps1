param()
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Path '.test-tmp' -Force | Out-Null
$testFolder = Join-Path '.test-tmp' ([guid]::NewGuid().ToString('N'))
& .venv/Scripts/python.exe -m pytest -q -c backend/pyproject.toml backend/tests --basetemp $testFolder
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
& .venv/Scripts/python.exe -m ruff check backend/app backend/tests
if ($LASTEXITCODE -ne 0) { throw 'Backend lint failed' }
& .venv/Scripts/python.exe -m mypy --config-file backend/pyproject.toml backend/app
if ($LASTEXITCODE -ne 0) { throw 'Python type check failed' }
npm.cmd run lint --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Frontend formatting check failed' }
npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
npm.cmd run test:e2e --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'Browser tests failed' }
