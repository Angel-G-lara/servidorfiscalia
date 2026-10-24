import jwt from 'jsonwebtoken';
import { supabase, supabaseAdmin } from '../config/supabase.js';
import crypto from 'crypto';

// Iniciar sesión con Google OAuth
export const googleLogin = async (req, res) => {
  try {
    const { idToken, device } = req.body;

    if (!idToken) {
      return res.status(400).json({ error: 'Token de Google requerido' });
    }

    // Verificar token con Google (requiere instalación de google-auth-library)
    // Por ahora, simulamos la verificación
    // En producción, usar: const ticket = await client.verifyIdToken({ idToken });

    // Buscar o crear usuario en Supabase
    const { data: existingUser, error: findError } = await supabase
      .from('users')
      .select('*')
      .eq('google_id', idToken)
      .single();

    if (findError && findError.code !== 'PGRST116') {
      throw findError;
    }

    let user;
    
    if (existingUser) {
      user = existingUser;
      
      if (!user.active) {
        return res.status(401).json({ error: 'Cuenta desactivada' });
      }
    } else {
      // Crear nuevo usuario
      // En producción, obtener email y nombre del token de Google
      const newUserId = crypto.randomUUID();
      const { data: newUser, error: createError } = await supabaseAdmin
        .from('users')
        .insert({
          id: newUserId,
          google_id: idToken,
          username: `user_${newUserId.substring(0, 8)}`,
          role: 'agente',
          unit: 'DEMO_A',
          active: true
        })
        .select()
        .single();

      if (createError) throw createError;
      user = newUser;
    }

    // Generar JWT
    const token = jwt.sign(
      { userId: user.id, role: user.role, unit: user.unit },
      process.env.JWT_SECRET,
      { expiresIn: '30d' }
    );

    // Registrar en auditoría
    await supabase.from('audit').insert({
      event_type: 'login_success',
      user_id: user.id,
      device: device || 'unknown',
      metadata: { method: 'google_oauth' }
    });

    res.json({
      user: {
        id: user.id,
        username: user.username,
        role: user.role,
        unit: user.unit,
        active: user.active
      },
      token
    });
  } catch (error) {
    console.error('Error en login de Google:', error);
    res.status(500).json({ error: 'Error al iniciar sesión' });
  }
};

// Obtener usuario actual
export const getCurrentUser = async (req, res) => {
  try {
    const { data: user, error } = await supabase
      .from('users')
      .select('id, username, role, unit, active')
      .eq('id', req.user.id)
      .single();

    if (error) throw error;

    res.json({ user });
  } catch (error) {
    console.error('Error al obtener usuario:', error);
    res.status(500).json({ error: 'Error al obtener usuario' });
  }
};

// Cerrar sesión
export const logout = async (req, res) => {
  try {
    // Registrar en auditoría
    await supabase.from('audit').insert({
      event_type: 'logout',
      user_id: req.user.id,
      device: req.body.device || 'unknown'
    });

    res.json({ ok: true });
  } catch (error) {
    console.error('Error al cerrar sesión:', error);
    res.status(500).json({ error: 'Error al cerrar sesión' });
  }
};
