# Guía paso a paso para configurar .env

## Paso 1: Configurar Supabase

### 1.1 Crear cuenta y proyecto
1. Ve a https://supabase.com
2. Crea una cuenta gratuita
3. Crea un nuevo proyecto (puede tardar 1-2 minutos)

### 1.2 Obtener credenciales de Supabase
1. En tu proyecto, ve a **Settings** > **API**
2. Copia estos tres valores:
   - **Project URL**: (ejemplo: `https://xyzabc.supabase.co`)
   - **anon public key**: (una clave larga que empieza con `eyJ...`)
   - **service_role key**: (otra clave larga, NO compartirla)

### 1.3 Ejecutar el schema SQL
1. En tu proyecto Supabase, ve a **SQL Editor**
2. Crea un "New query"
3. Copia el contenido del archivo `supabase-schema.sql` que está en la carpeta backend
4. Pégalo en el editor SQL
5. Haz clic en **Run** (bottom right)
6. Verifica que se creen las tablas: users, documents, versions, audit, device_events

## Paso 2: Configurar Google OAuth

### 2.1 Crear proyecto en Google Cloud Console
1. Ve a https://console.cloud.google.com
2. Crea un nuevo proyecto o selecciona uno existente
3. Nombre del proyecto: `Fiscalia Backend` (o el que prefieras)

### 2.2 Habilitar Google Sign-In
1. En el menú, ve a **APIs & Services** > **Library**
2. Busca "Google Identity"
3. Habilita "Google Identity Platform API"

### 2.3 Crear credenciales OAuth 2.0
1. Ve a **APIs & Services** > **Credentials**
2. Haz clic en **Create Credentials** > **OAuth client ID**
3. Configura:
   - **Application type**: Web application
   - **Name**: Fiscalia Backend
4. En **Authorized redirect URIs**, agrega:
   - `http://localhost:3000/api/auth/google/callback`
   - `http://127.0.0.1:3000/api/auth/google/callback`
5. Haz clic en **Create**
6. Copia:
   - **Client ID**: (un string largo)
   - **Client Secret**: (otro string largo)

### 2.4 Configurar pantalla de consentimiento
1. Ve a **APIs & Services** > **OAuth consent screen**
2. Configura:
   - **User Type**: External
   - **App name**: Fiscalia App
   - **User support email**: tu email
   - **Developer contact**: tu email
3. Haz clic en **Save and Continue** en cada paso

## Paso 3: Crear el archivo .env

### 3.1 Crear el archivo
Como `.env` está en `.gitignore`, necesitas crearlo manualmente:

**En Windows (PowerShell):**
```powershell
cd backend
New-Item -Path .env -ItemType File
```

**O simplemente crea el archivo manualmente en:**
`C:\Users\Admin\Documents\Codex\2026-10-24\te-incorporas-a-nuestro-equipo-del\outputs\servidor_fiscalia\backend\.env`

### 3.2 Copiar el contenido
Abre el archivo `.env` y pega esto:

```env
# Configuración del servidor
PORT=3000
NODE_ENV=development

# Supabase - REEMPLAZA ESTOS VALORES
SUPABASE_URL=https://TU_PROYECTO_SUPABASE.supabase.co
SUPABASE_ANON_KEY=TU_ANON_KEY_AQUI
SUPABASE_SERVICE_ROLE_KEY=TU_SERVICE_ROLE_KEY_AQUI

# Google OAuth - REEMPLAZA ESTOS VALORES
GOOGLE_CLIENT_ID=TU_GOOGLE_CLIENT_ID_AQUI
GOOGLE_CLIENT_SECRET=TU_GOOGLE_CLIENT_SECRET_AQUI
GOOGLE_CALLBACK_URL=http://localhost:3000/api/auth/google/callback

# JWT Secret - GENERA UNO ALEATORIO
JWT_SECRET=genera_una_clave_secreta_larga_y_aleatoria_aqui

# Configuración de archivos
MAX_FILE_SIZE=26214400
MAX_FILES=100
```

### 3.3 Reemplazar los valores

**Para SUPABASE_URL:**
- Reemplaza `https://TU_PROYECTO_SUPABASE.supabase.co` con tu URL real de Supabase
- Ejemplo: `https://abcdefg.supabase.co`

**Para SUPABASE_ANON_KEY:**
- Reemplaza `TU_ANON_KEY_AQUI` con el "anon public key" de Supabase
- Es una clave larga que empieza con `eyJ...`

**Para SUPABASE_SERVICE_ROLE_KEY:**
- Reemplaza `TU_SERVICE_ROLE_KEY_AQUI` con el "service_role key" de Supabase
- Esta clave es para operaciones admin en el servidor

**Para GOOGLE_CLIENT_ID:**
- Reemplaza `TU_GOOGLE_CLIENT_ID_AQUI` con el Client ID de Google
- Ejemplo: `123456789-abcde.apps.googleusercontent.com`

**Para GOOGLE_CLIENT_SECRET:**
- Reemplaza `TU_GOOGLE_CLIENT_SECRET_AQUI` con el Client Secret de Google
- Es una clave larga

**Para JWT_SECRET:**
- Reemplaza `genera_una_clave_secreta_larga_y_aleatoria_aqui` con una clave aleatoria
- Puedes generar una en: https://www.uuidgenerator.net/api/version4
- O usa cualquier string largo y aleatorio (mínimo 32 caracteres)

## Paso 4: Verificar configuración

Después de crear el `.env`, verifica que tenga este formato:

```env
PORT=3000
NODE_ENV=development
SUPABASE_URL=https://xyzabc.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GOOGLE_CLIENT_ID=123456789-abcde.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefg123456
GOOGLE_CALLBACK_URL=http://localhost:3000/api/auth/google/callback
JWT_SECRET=550e8400-e29b-41d4-a716-446655440000
MAX_FILE_SIZE=26214400
MAX_FILES=100
```

## Paso 5: Iniciar el servidor

```bash
cd backend
npm run dev
```

Deberías ver:
```
Servidor corriendo en puerto 3000
Ambiente: development
API: http://localhost:3000/api
```

## Paso 6: Probar el servidor

Abre en tu navegador:
- http://localhost:3000/api/health

Deberías ver:
```json
{
  "status": "ok",
  "mode": "development",
  "version": "1.0.0",
  "timestamp": "2026-10-24T..."
}
```

## Resumen rápido

1. ✅ Crea proyecto en Supabase → copia URL, anon key, service role key
2. ✅ Ejecuta `supabase-schema.sql` en SQL Editor de Supabase
3. ✅ Crea credenciales OAuth en Google Cloud Console → copia Client ID y Secret
4. ✅ Crea archivo `backend/.env` con tus credenciales
5. ✅ Ejecuta `npm run dev` en la carpeta backend

## Si tienes problemas

### Error: "Faltan variables de entorno de Supabase"
- Verifica que el archivo `.env` exista en la carpeta `backend/`
- Verifica que las variables tengan los valores correctos

### Error: "Project not found" de Supabase
- Verifica que la URL de Supabase sea correcta
- Verifica que el proyecto esté activo en Supabase

### Error de Google OAuth
- Verifica que el Client ID y Secret sean correctos
- Verifica que el redirect URI esté configurado en Google Console
- Verifica que la pantalla de consentimiento esté configurada

### No puedo crear el archivo .env
El archivo está en `.gitignore`, así que el sistema no me permite crearlo. Tú debes crearlo manualmente:
1. Abre la carpeta `backend` en tu explorador de archivos
2. Crea un nuevo archivo llamado `.env` (con el punto al inicio)
3. Pega el contenido con tus credenciales
4. Guarda el archivo
