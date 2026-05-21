# erp_readonly

`erp_readonly` is the only approved boundary for ERP RP Info reads in Sprint 001.

Runtime configuration must provide an ERP credential through `ERP_TESTE_DATABASE_URL`
or an equivalent vault/CI secret. The value must never be committed. The database
role should be read-only. If a dedicated read-only role is not available, the
adapter must force a read-only transaction, configure statement timeout, apply
`ERP_READONLY_MAX_ROWS`, and execute only allowlisted query names.

No application module outside this boundary may import an ERP driver or open a
direct ERP connection. The backend test suite scans for direct driver usage
outside the readonly boundary.
