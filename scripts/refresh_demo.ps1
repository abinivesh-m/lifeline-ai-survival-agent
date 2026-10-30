# Refresh the demo state in one command.
#
#   powershell -ExecutionPolicy Bypass -File scripts\refresh_demo.ps1
#
# 1. refuses to run with LIFELINE_OFFLINE=1 (that would flip the brain to the
#    deterministic policy and the section 04 panel would read OFFLINE POLICY)
# 2. runs the eight-step agent online, so the Open Weight brain answers live
#    (or the stored run is replayed and clearly labelled)
# 3. re-exports ui/public/data/lifeline.json from the fresh run
# 4. prints the exact badge numbers so the copy cannot drift from the artefact

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if ($env:LIFELINE_OFFLINE -eq "1") {
    throw "LIFELINE_OFFLINE=1 is set; unset it or the brain falls back to policy."
}

python agent.py --yes
if ($LASTEXITCODE -ne 0) { throw "agent.py exited $LASTEXITCODE" }

python export_ui_data.py
if ($LASTEXITCODE -ne 0) { throw "export_ui_data.py exited $LASTEXITCODE" }

$data = Get-Content "ui\public\data\lifeline.json" -Raw | ConvertFrom-Json
$proof = Get-Content "artifacts\openweight_proof.json" -Raw | ConvertFrom-Json
$valid = @($proof.runs | Where-Object { $_.valid }).Count
$brain = $data.allocation.brain

Write-Host ""
Write-Host "DEMO STATE (paste these, do not retype them)"
Write-Host ("  brain          {0} / {1} / {2} s" -f $brain.provider, $brain.model, $brain.latency_s)
Write-Host ("  brain status   {0}" -f $brain.status)
Write-Host ("  hero chip      ledger `${0:F4}/`${1:F0} live" -f $data.credit.spent_usd, $data.credit.budget_usd)
Write-Host ("  ledger rows    {0} rows, {1} models" -f $data.credit.ledger_rows, ($data.credit.by_model.PSObject.Properties | Measure-Object).Count)
Write-Host ("  proof badge    {0}/{1} valid" -f $valid, $proof.runs.Count)
Write-Host ("  proof latency  {0}" -f (($proof.runs | Where-Object { $_.valid } | ForEach-Object { "{0:F2} s" -f $_.latency_s }) -join " / "))
Write-Host ("  towns          {0} towns, {1} regions" -f $data.world.towns.Count, ($data.world.towns.region | Sort-Object -Unique).Count)

$ml = $data.multilingual
if ($ml.available) {
    Write-Host ("  payloads       {0}/{1} full · {2} voice · {3} decision · `${4:F4}" -f `
        $ml.totals.valid, $ml.totals.locales, $ml.totals.voice_scripts, $ml.totals.allocation_scripts, $ml.totals.cost_usd)
} else {
    Write-Warning "no multilingual artefact - the spoken panel will be empty (run python multilingual.py)."
}

if (Test-Path "artifacts\seri_gate.json") {
    $seri = Get-Content "artifacts\seri_gate.json" -Raw | ConvertFrom-Json
    Write-Host ("  seri gate      {0}/{1} approved · {2} spoken clips · `${3:F4}" -f `
        $seri.summary.approved, $seri.summary.languages, $seri.summary.spoken, `
        (($seri.locales | Measure-Object -Property cost_usd -Sum).Sum))
} else {
    Write-Warning "no seri_gate.json - the spoken-approval card will be empty (run python seri_gate.py)."
}

if (Test-Path "artifacts\voice_synth.json") {
    $voice = Get-Content "artifacts\voice_synth.json" -Raw | ConvertFrom-Json
    Write-Host ("  spoken         {0} clips · {1} s · {2} · `${3:F2}" -f `
        $voice.totals.clips, $voice.totals.seconds, $voice.engine.name, $voice.engine.cost_usd)
    if ($voice.skipped.Count -gt 0) {
        Write-Warning ("text-only locales: {0}" -f (($voice.skipped | ForEach-Object { $_.locale }) -join ", "))
    }
} else {
    Write-Warning "no voice_synth.json - run python voice_synth.py before recording."
}

if ($brain.status -ne "live") {
    Write-Warning "brain is '$($brain.status)', not live: check BASETEN_API_KEY, BASETEN_BASE_URL and the network before recording."
}
