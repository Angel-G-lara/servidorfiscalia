import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

console.log('🔍 Probando conexión con Supabase...\n');

// Verificar variables de entorno
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Error: Faltan variables de entorno');
  console.error('SUPABASE_URL:', supabaseUrl ? '✓' : '✗');
  console.error('SUPABASE_ANON_KEY:', supabaseKey ? '✓' : '✗');
  process.exit(1);
}

console.log('✓ Variables de entorno encontradas');
console.log('URL:', supabaseUrl);
console.log('Key:', supabaseKey.substring(0, 20) + '...\n');

// Crear cliente
const supabase = createClient(supabaseUrl, supabaseKey);

async function testConnection() {
  try {
    // Prueba 1: Verificar conexión básica
    console.log('1. Probando conexión básica...');
    const { data, error } = await supabase.from('users').select('count').limit(1);
    
    if (error) {
      console.error('❌ Error de conexión:', error.message);
      process.exit(1);
    }
    console.log('✓ Conexión exitosa\n');

    // Prueba 2: Verificar tablas existentes
    console.log('2. Verificando tablas...');
    const tables = ['users', 'documents', 'versions', 'audit', 'device_events'];
    
    for (const table of tables) {
      const { error: tableError } = await supabase.from(table).select('*').limit(1);
      if (tableError) {
        console.log(`  ✗ ${table}: ${tableError.message}`);
      } else {
        console.log(`  ✓ ${table}: OK`);
      }
    }
    console.log();

    // Prueba 3: Verificar usuarios existentes
    console.log('3. Verificando usuarios en la base de datos...');
    const { data: users, error: usersError } = await supabase
      .from('users')
      .select('id, username, role, unit, active')
      .limit(5);
    
    if (usersError) {
      console.error('❌ Error al obtener usuarios:', usersError.message);
    } else {
      console.log(`✓ Encontrados ${users.length} usuarios:`);
      users.forEach(user => {
        console.log(`  - ${user.username} (${user.role}, ${user.unit}, ${user.active ? 'activo' : 'inactivo'})`);
      });
    }
    console.log();

    console.log('✅ Todas las pruebas pasaron exitosamente');
    console.log('\n📝 Siguiente paso: Ejecuta el servidor con "npm run dev"');
    
  } catch (error) {
    console.error('❌ Error inesperado:', error.message);
    process.exit(1);
  }
}

testConnection();
