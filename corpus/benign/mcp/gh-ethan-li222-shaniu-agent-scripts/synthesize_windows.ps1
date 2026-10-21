$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$eventId = 'ShaniuSpeechProgress'
Register-ObjectEvent -InputObject $synth -EventName SpeakProgress -SourceIdentifier $eventId | Out-Null
try {
    $installed = $synth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'zh-CN' }
    if (-not $installed) { throw 'No Chinese desktop voice installed' }
    $synth.SelectVoice(($installed | Select-Object -First 1).VoiceInfo.Name)
    $synth.Rate = [int]$payload.rate
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $synth.SetOutputToWaveFile([string]$payload.output, $format)
    $synth.Speak([string]$payload.text)
    if ($payload.timings) {
        $boundaries = @(Get-Event -SourceIdentifier $eventId -ErrorAction SilentlyContinue | ForEach-Object {
            $args = $_.SourceEventArgs
            @{ start = $args.AudioPosition.TotalSeconds; position = $args.CharacterPosition; count = $args.CharacterCount; text = $args.Text }
        })
        $json = ConvertTo-Json -InputObject $boundaries -Depth 4 -Compress
        [System.IO.File]::WriteAllText([string]$payload.timings, $json, (New-Object System.Text.UTF8Encoding($false)))
    }
} finally {
    Unregister-Event -SourceIdentifier $eventId -ErrorAction SilentlyContinue
    Remove-Event -SourceIdentifier $eventId -ErrorAction SilentlyContinue
    $synth.Dispose()
}
