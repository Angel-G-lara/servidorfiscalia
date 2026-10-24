# Desplegar en Vercel

## Configuración para Vercel

Este proyecto está configurado como monorepo para desplegar en Vercel, ignorando la parte de Python.

## Estructura del Monorepo

```
servidorfiscalia/
├── backend/              # Backend Node.js (Express + Supabase)
│   ├── src/
│   ├── package.json
│   └── .env.example
├── api/                  # Entry point para Vercel
│   └── index.js
├── vercel.json           # Configuración de Vercel
└── .vercelignore         # Archivos a ignorar en el deploy
```

## Variables de Entorno en Vercel

Necesitas configurar estas variables en tu proyecto Vercel:

1. Ve a tu proyecto en Vercel
2. Settings > Environment Variables
3. Agrega las siguientes variables:

### Variables Requeridas

```
NODE_ENV=production
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu_anon_key
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
GOOGLE_CLIENT_ID=tu_google_client_id
GOOGLE_CLIENT_SECRET=tu_google_client_secret
GOOGLE_CALLBACK_URL=https://tu-dominio.vercel.app/api/auth/google/callback
JWT_SECRET=tu_jwt_secret
MAX_FILE_SIZE=26214400
MAX_FILES=100
```

### Notas Importantes

- **GOOGLE_CALLBACK_URL**: Debe ser tu dominio de Vercel + `/api/auth/google/callback`
- **JWT_SECRET**: Genera una clave aleatoria larga y segura
- **SUPABASE_SERVICE_ROLE_KEY**: Solo úsala en el servidor, nunca en el cliente

## Despliegue Automático

### Opción 1: Desde GitHub (Recomendado)

1. Asegúrate de que el código esté en GitHub
2. Ve a https://vercel.com/new
3. Importa tu repositorio: `https://github.com/Angel-G-lara/servidorfiscalia.git`
4. Vercel detectará automáticamente la configuración
5. Configura las variables de entorno
6. Haz clic en **Deploy**

### Opción 2: Desde CLI

```bash
# Instalar Vercel CLI
npm i -g vercel

# Login
vercel login

# Desplegar
vercel
```

## Configuración de Google OAuth para Producción

1. Ve a Google Cloud Console > APIs & Services > Credentials
2. Edita tu OAuth 2.0 Client ID
3. Agrega a **Authorized redirect URIs**:
   - `https://tu-dominio.vercel.app/api/auth/google/callback`
4. Guarda los cambios

## Dominio Personalizado (Opcional)

1. En Vercel, ve a Settings > Domains
2. Agrega tu dominio personal
3. Actualiza las configuraciones:
   - Google OAuth redirect URI
   - Variable `GOOGLE_CALLBACK_URL` en Vercel
   - Orígenes permitidos en CORS (en `backend/src/index.js`)

## Verificar el Despliegue

Después del despliegue, prueba:

```bash
# Health check
curl https://tu-dominio.vercel.app/api/health

# Debería retornar:
{
  "status": "ok",
  "mode": "production",
  "version": "1.0.0",
  "timestamp": "..."
}
```

## Actualizar Flutter para Producción

En tu app Flutter, actualiza la URL base:

```dart
// lib/services/api_service.dart
class ApiService {
  static const String baseUrl = 'https://tu-dominio.vercel.app';
  
  // ... resto del código
}
```

## Logs y Monitoreo

En Vercel:
- Ve a la pestaña **Deployments**
- Haz clic en tu último deployment
- Verifica los **Logs** para errores
- Usa **Analytics** para monitorear el tráfico

## Troubleshooting

### Error: "Module not found"
- Verifica que `serverless-http` esté en `package.json`
- Ejecuta `npm install` localmente para actualizar `package-lock.json`

### Error: "Environment variable not found"
- Verifica que todas las variables estén configuradas en Vercel
- Nombres de variables son case-sensitive

### Error de CORS en producción
- Actualiza la lista de orígenes permitidos en `backend/src/index.js`
- Agrega tu dominio de Vercel

### Error de Google OAuth
- Verifica que el redirect URI coincida exactamente
- Revisa la configuración de la pantalla de consentimiento

## Actualizar el Despliegue

Cada vez que hagas push a la rama `main` en GitHub, Vercel desplegará automáticamente.

Para deploy manual:
```bash
vercel --prod
```

## Limitaciones de Vercel

- **Timeout**: 30 segundos por defecto (configurado en `vercel.json`)
- **Body size**: 4.5 MB (Vercel limit) - necesitarás usar upload por chunks para archivos grandes
- **Rate limiting**: Configurado en el middleware (100 requests por 15 minutos)

## Costos

- Vercel: Free tier incluye 100GB bandwidth/mes
- Supabase: Free tier incluye 500MB database, 1GB storage
- Para producción, considera los planes pagos según el tráfico
