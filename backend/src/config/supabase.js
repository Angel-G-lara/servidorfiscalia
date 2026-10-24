import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Faltan variables de entorno de Supabase');
}

// Cliente para autenticación (anon key)
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Cliente con permisos elevados (service role key) - solo en servidor
export const supabaseAdmin = createClient(supabaseUrl, supabaseServiceRoleKey);
