// =============================================================================
// activity-log-export.bicep  (SKELETON)
// Sends the subscription activity log to BOTH the workspace (search, alerts)
// and the immutable archive (years, WORM). Subscription scope.
//
//   az deployment sub create --location eastus2 --template-file activity-log-export.bicep \
//     --parameters workspaceId=<id> archiveStorageId=<id>
// =============================================================================
targetScope = 'subscription'

param workspaceId string
param archiveStorageId string

var categories = [
  'Administrative'
  'Security'
  'Policy'
  'Alert'
  'ServiceHealth'
  'ResourceHealth'
]

resource toBoth 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'activity-to-workspace-and-archive'
  properties: {
    workspaceId: workspaceId
    storageAccountId: archiveStorageId
    logs: [for c in categories: {
      category: c
      enabled: true
    }]
  }
}
