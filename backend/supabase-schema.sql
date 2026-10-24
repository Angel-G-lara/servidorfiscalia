-- Esquema de base de datos para Supabase
-- Ejecutar esto en el SQL Editor de Supabase

-- Tabla de usuarios
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password TEXT, -- NULL si usa Google OAuth
  google_id TEXT UNIQUE, -- ID de Google OAuth
  role TEXT NOT NULL CHECK (role IN ('admin', 'revisor', 'agente', 'auditor')),
  unit TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de documentos
CREATE TABLE documents (
  id TEXT PRIMARY KEY,
  unit TEXT NOT NULL,
  title TEXT NOT NULL,
  owner TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de versiones
CREATE TABLE versions (
  id TEXT PRIMARY KEY,
  doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  number INTEGER NOT NULL,
  digest TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
  files TEXT NOT NULL, -- JSON con manifiesto de archivos
  author TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  reviewer TEXT REFERENCES users(id),
  reviewed TIMESTAMP WITH TIME ZONE,
  note TEXT,
  UNIQUE(doc_id, number)
);

-- Tabla de auditoría
CREATE TABLE audit (
  id BIGSERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,
  user_id TEXT REFERENCES users(id),
  unit TEXT,
  device TEXT,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de eventos del dispositivo
CREATE TABLE device_events (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  device TEXT NOT NULL,
  event_id TEXT NOT NULL,
  action TEXT NOT NULL,
  metadata JSONB,
  local_time TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, device, event_id)
);

-- Índices para mejor rendimiento
CREATE INDEX idx_documents_unit ON documents(unit);
CREATE INDEX idx_versions_doc_id ON versions(doc_id);
CREATE INDEX idx_versions_status ON versions(status);
CREATE INDEX idx_audit_user_id ON audit(user_id);
CREATE INDEX idx_audit_created_at ON audit(created_at DESC);
CREATE INDEX idx_device_events_user_id ON device_events(user_id);

-- Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_events ENABLE ROW LEVEL SECURITY;

-- Políticas RLS para usuarios
CREATE POLICY "Admins pueden ver todos los usuarios" ON users
  FOR SELECT USING (role = 'admin');

CREATE POLICY "Usuarios pueden ver su propio perfil" ON users
  FOR SELECT USING (id = auth.uid()::text);

-- Políticas RLS para documentos
CREATE POLICY "Usuarios pueden ver documentos de su unidad" ON documents
  FOR SELECT USING (unit = (SELECT unit FROM users WHERE id = auth.uid()::text));

CREATE POLICY "Usuarios pueden crear documentos en su unidad" ON documents
  FOR INSERT WITH CHECK (unit = (SELECT unit FROM users WHERE id = auth.uid()::text) AND owner = auth.uid()::text);

-- Políticas RLS para versiones
CREATE POLICY "Usuarios pueden ver versiones de su unidad" ON versions
  FOR SELECT USING (
    doc_id IN (SELECT id FROM documents WHERE unit = (SELECT unit FROM users WHERE id = auth.uid()::text))
  );

CREATE POLICY "Usuarios pueden crear versiones" ON versions
  FOR INSERT WITH CHECK (author = auth.uid()::text);

CREATE POLICY "Revisores pueden actualizar versiones" ON versions
  FOR UPDATE USING (
    author = auth.uid()::text OR 
    (SELECT role FROM users WHERE id = auth.uid()::text) IN ('admin', 'revisor')
  );

-- Políticas RLS para auditoría
CREATE POLICY "Admins pueden ver toda la auditoría" ON audit
  FOR SELECT USING ((SELECT role FROM users WHERE id = auth.uid()::text) = 'admin');

CREATE POLICY "Usuarios pueden ver auditoría de su unidad" ON audit
  FOR SELECT USING (unit = (SELECT unit FROM users WHERE id = auth.uid()::text));

CREATE POLICY "Admins pueden insertar auditoría" ON audit
  FOR INSERT WITH CHECK ((SELECT role FROM users WHERE id = auth.uid()::text) = 'admin');

-- Políticas RLS para eventos del dispositivo
CREATE POLICY "Usuarios pueden ver sus propios eventos" ON device_events
  FOR SELECT USING (user_id = auth.uid()::text);

CREATE POLICY "Usuarios pueden insertar sus eventos" ON device_events
  FOR INSERT WITH CHECK (user_id = auth.uid()::text);

-- Crear usuario admin inicial
INSERT INTO users (id, username, password, role, unit, active)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'admin',
  '$2a$10$abcdefghijklmnopqrstuvwxyz1234567890', -- Cambiar esto por hash real
  'admin',
  'DEMO_A',
  1
);
