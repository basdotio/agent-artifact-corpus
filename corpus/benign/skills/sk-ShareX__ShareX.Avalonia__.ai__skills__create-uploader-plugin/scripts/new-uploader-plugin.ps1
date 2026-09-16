param(
    [Parameter(Mandatory = $true)]
    [string]$PluginName,

    [string]$PluginId = "",

    [string]$DisplayName = "",

    [string]$OutputRoot = "src\\desktop\\plugins",

    [string]$SolutionPath = "src\\desktop\\XerahS.sln",

    [switch]$AddToSolution,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-ToPascalCase {
    param([string]$Value)

    $parts = @([regex]::Split($Value, "[^A-Za-z0-9]+") | Where-Object { $_ })
    if ($parts.Count -eq 0) {
        throw "Unable to derive a valid plugin name from '$Value'."
    }

    return ($parts | ForEach-Object {
        if ($_.Length -eq 1) {
            $_.ToUpperInvariant()
        }
        else {
            $_.Substring(0, 1).ToUpperInvariant() + $_.Substring(1)
        }
    }) -join ""
}

function Convert-ToPluginId {
    param([string]$Value)

    $clean = ($Value -replace "[^A-Za-z0-9]+", "").ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($clean)) {
        throw "Unable to derive a valid plugin id from '$Value'."
    }

    return $clean
}

function Write-Utf8File {
    param(
        [string]$Path,
        [string]$Content
    )

    $directory = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($directory) -and -not (Test-Path $directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Apply-Tokens {
    param(
        [string]$Content,
        [hashtable]$Tokens
    )

    $result = $Content
    foreach ($key in $Tokens.Keys) {
        $result = $result.Replace($key, $Tokens[$key])
    }

    return $result
}

function Get-OutputRelativePath {
    param(
        [string]$TemplateRelativePath,
        [hashtable]$Tokens
    )

    $normalizedTemplatePath = $TemplateRelativePath.Replace("/", "\")

    switch ($normalizedTemplatePath) {
        "Plugin.csproj.tmpl" { return "$($Tokens.__ASSEMBLY_NAME__).csproj" }
        "plugin.json.tmpl" { return "plugin.json" }
        "ConfigModel.cs.tmpl" { return "$($Tokens.__CONFIG_MODEL_CLASS__).cs" }
        "Provider.cs.tmpl" { return "$($Tokens.__PROVIDER_CLASS__).cs" }
        "Uploader.cs.tmpl" { return "$($Tokens.__UPLOADER_CLASS__).cs" }
        "ViewModels\ConfigViewModel.cs.tmpl" { return "ViewModels\$($Tokens.__CONFIG_VIEWMODEL_CLASS__).cs" }
        "Views\ConfigView.axaml.tmpl" { return "Views\$($Tokens.__CONFIG_VIEW_CLASS__).axaml" }
        "Views\ConfigView.axaml.cs.tmpl" { return "Views\$($Tokens.__CONFIG_VIEW_CLASS__).axaml.cs" }
        default { throw "Unmapped template file: $TemplateRelativePath" }
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..\\..")).Path
$templateRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\assets\\desktop-plugin-template")).Path
$pluginStemInput = $PluginName -replace "\.Plugin$", ""
$pluginStem = Convert-ToPascalCase $pluginStemInput
$resolvedPluginId = if ([string]::IsNullOrWhiteSpace($PluginId)) { Convert-ToPluginId $pluginStem } else { Convert-ToPluginId $PluginId }
$resolvedDisplayName = if ([string]::IsNullOrWhiteSpace($DisplayName)) { "$pluginStem Uploader" } else { $DisplayName.Trim() }

$assemblyName = "XerahS.$pluginStem.Plugin"
$namespaceName = "ShareX.$pluginStem.Plugin"
$providerClass = "${pluginStem}Provider"
$uploaderClass = "${pluginStem}Uploader"
$configModelClass = "${pluginStem}ConfigModel"
$configViewModelClass = "${pluginStem}ConfigViewModel"
$configViewClass = "${pluginStem}ConfigView"
$folderName = "$pluginStem.Plugin"
$pluginsRoot = Join-Path $repoRoot $OutputRoot
$projectDirectory = Join-Path $pluginsRoot $folderName
$projectPath = Join-Path $projectDirectory "$assemblyName.csproj"
$resolvedSolutionPath = Join-Path $repoRoot $SolutionPath

if ((Test-Path $projectDirectory) -and -not $Force) {
    throw "Plugin directory already exists: $projectDirectory. Use -Force to overwrite."
}

if (Test-Path $projectDirectory) {
    Remove-Item -Recurse -Force $projectDirectory
}

New-Item -ItemType Directory -Force -Path $projectDirectory | Out-Null

$tokens = @{
    "__PLUGIN_STEM__" = $pluginStem
    "__PLUGIN_ID__" = $resolvedPluginId
    "__DISPLAY_NAME__" = $resolvedDisplayName
    "__ASSEMBLY_NAME__" = $assemblyName
    "__NAMESPACE__" = $namespaceName
    "__PROVIDER_CLASS__" = $providerClass
    "__UPLOADER_CLASS__" = $uploaderClass
    "__CONFIG_MODEL_CLASS__" = $configModelClass
    "__CONFIG_VIEWMODEL_CLASS__" = $configViewModelClass
    "__CONFIG_VIEW_CLASS__" = $configViewClass
}

$templateFiles = Get-ChildItem -Path $templateRoot -Recurse -File
foreach ($templateFile in $templateFiles) {
    $relativeTemplatePath = $templateFile.FullName.Substring($templateRoot.Length + 1)
    $outputRelativePath = Get-OutputRelativePath $relativeTemplatePath $tokens
    $outputPath = Join-Path $projectDirectory $outputRelativePath
    $content = Get-Content -Raw $templateFile.FullName
    $rendered = Apply-Tokens $content $tokens
    Write-Utf8File -Path $outputPath -Content $rendered
}

if ($AddToSolution) {
    if (-not (Test-Path $resolvedSolutionPath)) {
        throw "Solution file not found: $resolvedSolutionPath"
    }

    & dotnet sln $resolvedSolutionPath add $projectPath --solution-folder Plugins
    if (-not $?) {
        throw "Failed to add plugin project to solution."
    }
}

Write-Host "Created plugin scaffold:"
Write-Host "  Folder: $projectDirectory"
Write-Host "  Project: $projectPath"
Write-Host "  PluginId: $resolvedPluginId"
Write-Host "  DisplayName: $resolvedDisplayName"

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Implement upload logic in $uploaderClass.cs"
Write-Host "  2. Tighten validation and settings in $providerClass.cs and $configModelClass.cs"
Write-Host "  3. Replace the generic config UI with service-specific fields if needed"
Write-Host "  4. Build with: dotnet build $projectPath -m:1"
