# policy: allow-erp-migration-read
path "secret/data/erp/*" {
  capabilities = ["read", "list"]
}

