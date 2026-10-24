# Backend Node.js - Fiscalía Documental

Backend en Node.js con Express para gestión documental fiscalía, integrado con Supabase y autenticación Google OAuth.

## Estructura del Monorepo

```
servidor_fiscalia/
├── backend/              # Backend Node.js
│   ├── src/
│   │   ├── config/       # Configuración (Supabase)
│   │   ├── controllers/  # Controladores de la API
│   │   ├── middleware/   # Middleware (auth, CORS)
│   │   ├── routes/       # Rutas de Express
│   │   ├── services/     # Servicios de negocio
│   │   └── utils/        # Utilidades
│   ├── package.json
│   └── .env.example
└── frontend/             # App Flutter (próximamente)
```

## Requisitos Previos

- Node.js 18+ 
- Supabase account (https://supabase.com)
- Google Cloud Console project (para OAuth)

## Instalación

1. **Instalar dependencias**
```bash
cd backend
npm install
```

2. **Configurar Supabase**
   - Crea un proyecto en https://supabase.com
   - Ve a Settings > API y copia:
     - Project URL
     - anon public key
     - service_role key (requerido para operaciones admin)
   - Ejecuta el SQL en `supabase-schema.sql` en el SQL Editor de Supabase

3. **Configurar Google OAuth**
   - Ve a Google Cloud Console > APIs & Services > Credentials
   - Crea credenciales OAuth 2.0
   - Agrega tu dominio a "Authorized redirect URIs"
   - Copia Client ID y Client Secret

4. **Configurar variables de entorno**
```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:
```env
PORT=3000
NODE_ENV=development

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_CALLBACK_URL=http://localhost:3000/api/auth/google/callback

JWT_SECRET=your-secret-key-change-this
```

5. **Iniciar el servidor**
```bash
npm run dev    # Desarrollo con hot-reload
npm start      # Producción
```

El servidor estará disponible en `http://localhost:3000`

## API Endpoints

### Autenticación
- `POST /api/auth/google` - Login con Google OAuth
- `GET /api/auth/me` - Obtener usuario actual
- `POST /api/auth/logout` - Cerrar sesión

### Documentos
- `GET /api/documents` - Listar documentos
- `POST /api/documents` - Subir documento
- `POST /api/documents/sync/manifest` - Obtener manifiesto de sincronización
- `POST /api/documents/:version_id/review` - Revisar versión

### Usuarios (Solo admin)
- `GET /api/users` - Listar usuarios
- `POST /api/users` - Crear usuario
- `POST /api/users/:id/active` - Activar/desactivar usuario

### Auditoría
- `GET /api/audit` - Ver eventos de auditoría
- `GET /api/audit/verify` - Verificar cadena de auditoría
- `POST /api/audit/device-events` - Registrar eventos del dispositivo

### Health
- `GET /api/health` - Health check

## Flutter Integration

El backend está configurado para aceptar conexiones desde Flutter:

### CORS configurado para:
- `http://localhost:3000` - Desarrollo web
- `http://127.0.0.1:3000` - Desarrollo web
- `http://10.0.2.2:3000` - Emulador Android (localhost del host)
- Tu dominio de producción

### Ejemplo de llamada desde Flutter:

```dart
final response = await http.post(
  Uri.parse('http://10.0.2.2:3000/api/auth/google'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'idToken': googleIdToken,
    'device': 'android_device_id'
  }),
);
```

## Roles y Permisos

- **admin**: Acceso total, puede crear usuarios y ver toda la auditoría
- **revisor**: Puede aprobar/rechazar documentos de su unidad
- **agente**: Puede subir documentos y ver los de su unidad
- **auditor**: Solo puede ver auditoría, sin acceso a documentos

## Seguridad

- JWT tokens para autenticación
- Helmet para headers de seguridad
- Rate limiting para prevenir abuso
- Row Level Security (RLS) en Supabase
- CORS configurado para orígenes permitidos

## Desarrollo

El servidor usa `--watch` de Node.js para hot-reload en desarrollo:
```bash
npm run dev
```

## Producción

1. Configura `NODE_ENV=production` en `.env`
2. Usa un JWT secreto fuerte
3. Configura CORS solo para tu dominio de producción
4. Usa HTTPS
5. Configura Supabase con RLS apropiado

## Troubleshooting

### Error: "Faltan variables de entorno de Supabase"
Verifica que `.env` existe y tiene las credenciales de Supabase.

### Error: "No permitido por CORS"
Verifica que el origen de tu app Flutter esté en la lista de orígenes permitidos en `src/index.js`.

### Error: "Usuario no encontrado"
Verifica que el usuario exista en Supabase y esté activo.

## Próximos Pasos

- Implementar carga de archivos con storage de Supabase
- Agregar tests unitarios
- Implementar verificación HMAC para auditoría
- Agregar logging estructurado
- Implementar websockets para notificaciones en tiempo real
