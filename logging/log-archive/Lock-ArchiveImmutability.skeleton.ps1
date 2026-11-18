<#
.SYNOPSIS
    SKELETON. Locks the WORM immutability policy on the audit archive.
    THIS CANNOT BE UNDONE.

.DESCRIPTION
    Once locked:
      - the retention period can be extended but never shortened or removed
      - no blob in the container can be changed or deleted until it expires
      - the storage account cannot be deleted while any blob is still retained

    The build leaves the policy unlocked so it can be tested. This script is
    handed to the system owner, who runs it after a written decision. Without
    -Lock it only reports the current state.

    Guards: -Lock must be given, the account name must be typed back, and
    PowerShell's own confirmation (ConfirmImpact High) still applies.

.EXAMPLE
    ./Lock-ArchiveImmutability.skeleton.ps1 -ResourceGroupName <rg> -StorageAccountName <name>
    ./Lock-ArchiveImmutability.skeleton.ps1 -ResourceGroupName <rg> -StorageAccountName <name> -Lock -DecisionReference CHG-0000
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)] [string] $ResourceGroupName,
    [Parameter(Mandatory)] [string] $StorageAccountName,
    [string] $ContainerName = 'audit-archive',
    [switch] $Lock,
    [string] $DecisionReference
)

$ErrorActionPreference = 'Stop'

$policy = Get-AzRmStorageContainerImmutabilityPolicy -ResourceGroupName $ResourceGroupName `
    -StorageAccountName $StorageAccountName -ContainerName $ContainerName

$years = [math]::Round($policy.ImmutabilityPeriodSinceCreationInDays / 365, 1)
Write-Host ("Container  : {0}/{1}" -f $StorageAccountName, $ContainerName)
Write-Host ("State      : {0}" -f $policy.State)
Write-Host ("Retention  : {0} days (about {1} years)" -f $policy.ImmutabilityPeriodSinceCreationInDays, $years)

if (-not $Lock) {
    Write-Host "`nReport only. Add -Lock to lock (irreversible)."
    return
}
if ($policy.State -eq 'Locked') { Write-Host 'Already locked. Nothing to do.'; return }
if (-not $DecisionReference) { throw 'Give -DecisionReference: the change or decision record that approves locking.' }

Write-Warning "Locking makes $years years of retention permanent. The account cannot be deleted until then."
$typed = Read-Host "Type the storage account name to confirm"
if ($typed -ne $StorageAccountName) { throw 'Name did not match. Nothing changed.' }

if ($PSCmdlet.ShouldProcess("$StorageAccountName/$ContainerName", "LOCK immutability policy ($DecisionReference)")) {
    Lock-AzRmStorageContainerImmutabilityPolicy -ResourceGroupName $ResourceGroupName `
        -StorageAccountName $StorageAccountName -ContainerName $ContainerName -Etag $policy.Etag -Force | Out-Null
    $after = Get-AzRmStorageContainerImmutabilityPolicy -ResourceGroupName $ResourceGroupName `
        -StorageAccountName $StorageAccountName -ContainerName $ContainerName
    Write-Host ("State now  : {0}   decision: {1}   at {2:u}" -f $after.State, $DecisionReference, (Get-Date).ToUniversalTime())
}
