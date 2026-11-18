// =============================================================================
// log-archive.bicep  (SKELETON)
// Long-term, tamper-evident archive for audit logs.
//
//   Log Analytics keeps 90-365 days for searching. This storage account keeps
//   years, as WORM (write once, read many) blobs that nobody can edit or delete
//   until the retention period ends, not even an Owner.
//
//   The immutability policy is created UNLOCKED, on purpose:
//     unlocked : retention can still be shortened or removed. Lets you test.
//     locked   : retention can only be extended, never shortened, and the
//                storage account cannot be deleted until the last blob expires.
//   Locking is a one-way door, so it is a decision for the system owner, made
//   in writing, then done with Lock-ArchiveImmutability.skeleton.ps1.
//
// Deploy into the platform resource group:
//   az deployment group create -g <platform-rg> --template-file log-archive.bicep \
//     --parameters namePrefix=contosoplatprd retentionDays=2555
// =============================================================================
@description('Lowercase letters and numbers only (storage naming).')
@maxLength(15)
param namePrefix string

param location string = resourceGroup().location

@description('WORM retention in days. 2555 days = 7 years.')
@minValue(1)
@maxValue(146000)
param retentionDays int = 2555

@description('Days before archived logs move to the cool tier.')
param coolAfterDays int = 30

@description('Days before archived logs move to the archive tier.')
param archiveAfterDays int = 180

@description('Allow account-key access. Off unless a writer genuinely needs it; record the reason if turned on.')
param allowSharedKeyAccess bool = false

param tags object = {}

resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${namePrefix}logarch01'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_GRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: allowSharedKeyAccess
    // "Selected networks" rather than Disabled: diagnostic settings write here as
    // a trusted Azure service, and that exception only applies through networkAcls.
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: sa
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 30
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 30
    }
  }
}

// Diagnostic settings write into containers named insights-logs-* and
// insights-activity-logs. Those are created by Azure on first write, so the
// WORM policy is applied here to a container created up front, and the
// TODO below moves the policy to account level for full coverage.
resource archive 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blob
  name: 'audit-archive'
  properties: {
    publicAccess: 'None'
  }
}

resource worm 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2023-05-01' = {
  parent: archive
  name: 'default'
  properties: {
    immutabilityPeriodSinceCreationInDays: retentionDays
    allowProtectedAppendWrites: true
  }
}

resource lifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: sa
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'tier-down-audit-logs'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [
                'blockBlob'
                'appendBlob'
              ]
            }
            actions: {
              baseBlob: {
                tierToCool: {
                  daysAfterModificationGreaterThan: coolAfterDays
                }
                tierToArchive: {
                  daysAfterModificationGreaterThan: archiveAfterDays
                }
              }
            }
          }
        }
      ]
    }
  }
}

// TODO (full build):
//  - version-level immutability at account level, so containers Azure creates
//    later (insights-logs-*) inherit the WORM policy
//  - private endpoint for blob, linked to the hub private DNS zone
//  - diagnostic settings on this account itself (who read the archive)

output storageAccountId string = sa.id
output storageAccountName string = sa.name
output immutabilityState string = 'Unlocked'
