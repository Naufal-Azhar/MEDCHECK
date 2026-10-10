# Database

Database migrations are plain SQL files in `db/migrations/` and are applied in filename order.

Apply the initial schema from the project root:

```powershell
Get-Content .\db\migrations\001_initial_schema.sql | docker compose exec -T postgres psql -U forgehacks -d forgehacks
```

The initial schema intentionally leaves the embedding vector dimension unspecified. The dimension will be locked after the embedding model is selected and verified.
