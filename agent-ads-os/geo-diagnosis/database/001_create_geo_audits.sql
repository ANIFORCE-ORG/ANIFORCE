CREATE TABLE IF NOT EXISTS geo_audits (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  brand TEXT NOT NULL,
  domain TEXT NOT NULL,
  category TEXT NOT NULL,
  market TEXT,
  report_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_geo_audits_project_id ON geo_audits(project_id);
CREATE INDEX IF NOT EXISTS idx_geo_audits_brand ON geo_audits(brand);
CREATE INDEX IF NOT EXISTS idx_geo_audits_domain ON geo_audits(domain);
CREATE INDEX IF NOT EXISTS idx_geo_audits_created_at ON geo_audits(created_at);
