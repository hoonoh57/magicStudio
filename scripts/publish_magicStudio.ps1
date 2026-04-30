param(
    [string]$Repo = "hoonoh57/magicStudio",
    [string]$Visibility = "public"
)

$ErrorActionPreference = "Stop"

Write-Host "== magicStudio GitHub publish script =="

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI(gh)가 필요합니다. https://cli.github.com/ 설치 후 'gh auth login'을 먼저 실행하세요."
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git이 필요합니다."
}

$repoName = $Repo.Split("/")[-1]

if (-not (Test-Path ".git")) {
    git init
}

git add .
git commit -m "docs: bootstrap magicStudio project rules" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "No new commit created. Continuing..."
}

$existing = gh repo view $Repo --json nameWithOwner 2>$null
if ($LASTEXITCODE -ne 0) {
    gh repo create $Repo --$Visibility --source . --remote origin --push
} else {
    git remote remove origin 2>$null
    git remote add origin "https://github.com/$Repo.git"
    git branch -M main
    git push -u origin main
}

Write-Host "Published: https://github.com/$Repo"
