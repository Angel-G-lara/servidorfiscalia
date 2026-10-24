#!/bin/bash
# Script para iniciar el servidor en modo demo (sin Supabase real)
# NOTA: Este es solo para verificar que el servidor inicia correctamente
# Para uso real, configura las credenciales de Supabase en .env

export PORT=3000
export NODE_ENV=development
export SUPABASE_URL=https://demo.supabase.co
export SUPABASE_ANON_KEY=demo_key
export SUPABASE_SERVICE_ROLE_KEY=demo_service_key
export GOOGLE_CLIENT_ID=demo_client_id
export GOOGLE_CLIENT_SECRET=demo_client_secret
export JWT_SECRET=demo_secret_change_in_production

node src/index.js
