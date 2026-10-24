import { supabase, supabaseAdmin } from '../config/supabase.js';
import crypto from 'crypto';
import bcrypt from 'bcryptjs';

// Obtener todos los usuarios (solo admin)
export const getUsers = async (req, res) => {
  try {
    const { data: users, error } = await supabase
      .from('users')
      .select('id, username, role, unit, active')
      .order('username');

    if (error) throw error;

    res.json({ users });
  } catch (error) {
    console.error('Error al obtener usuarios:', error);
    res.status(500).json({ error: 'Error al obtener usuarios' });
  }
};

// Crear usuario (solo admin)
export const createUser = async (req, res) => {
  try {
    const { username, password, role, unit } = req.body;

    if (!username || !password || !role || !unit) {
      return res.status(400).json({ error: 'Faltan campos requeridos' });
    }

    if (!['admin', 'revisor', 'agente', 'auditor'].includes(role)) {
      return res.status(400).json({ error: 'Rol inválido' });
    }

    if (password.length < 12) {
      return res.status(400).json({ error: 'La contraseña debe tener al menos 12 caracteres' });
    }

    // Verificar si usuario existe
    const { data: existing } = await supabase
      .from('users')
      .select('id')
      .eq('username', username)
      .single();

    if (existing) {
      return res.status(409).json({ error: 'El usuario ya existe' });
    }

    // Crear usuario
    const userId = crypto.randomUUID();
    const hashedPassword = await bcrypt.hash(password, 10);

    const { error } = await supabaseAdmin
      .from('users')
      .insert({
        id: userId,
        username,
        password: hashedPassword,
        role,
        unit,
        active: true
      });

    if (error) throw error;

    // Registrar en auditoría
    await supabase.from('audit').insert({
      event_type: 'user_created',
      user_id: req.user.id,
      metadata: {
        target_user: userId,
        role,
        unit
      }
    });

    res.status(201).json({ id: userId });
  } catch (error) {
    console.error('Error al crear usuario:', error);
    res.status(500).json({ error: 'Error al crear usuario' });
  }
};

// Activar/desactivar usuario (solo admin)
export const toggleUserActive = async (req, res) => {
  try {
    const { id } = req.params;
    const { active } = req.body;

    if (id === req.user.id) {
      return res.status(400).json({ error: 'No puede desactivar su propia cuenta' });
    }

    const { error } = await supabaseAdmin
      .from('users')
      .update({ active })
      .eq('id', id);

    if (error) throw error;

    // Registrar en auditoría
    await supabase.from('audit').insert({
      event_type: 'user_status_changed',
      user_id: req.user.id,
      metadata: {
        target_user: id,
        active
      }
    });

    res.json({ ok: true });
  } catch (error) {
    console.error('Error al cambiar estado de usuario:', error);
    res.status(500).json({ error: 'Error al cambiar estado de usuario' });
  }
};
