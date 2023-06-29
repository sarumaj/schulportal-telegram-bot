param (
    # path to an .env file
    [Parameter(Mandatory=$true)]
    [string]$path
)

$variables = Select-String -Path $path -Pattern '^\s*[^\s=#]+=[^\s]+$' -Raw

foreach($var in $variables) {
    $keyVal = $var -split '=', 2
    $key = $keyVal[0].Trim()
    $val = $keyVal[1].Trim("'").Trim('"')
    [Environment]::SetEnvironmentVariable($key, $val)
    Write-Host "$key=$([Environment]::GetEnvironmentVariable($key))"
}