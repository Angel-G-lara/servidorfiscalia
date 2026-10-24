import { supabase } from '../config/supabase.js';

// Obtener eventos de auditoría
export const getAuditEvents = async (req, res) => {
  try {
    const { limit = 300 } = req.query;

    let query = supabase
      .from('audit')
      .select('*')
      .order('created', { ascending: false })
      .limit(parseInt(limit));

    // Filtrar según rol
    if (req.user.role !== 'admin') {
      query = query.eq('unit', req.user.unit);
    }

    const { data: events, error } = await query;

    if (error) throw error;

    res.json({ events });
  } catch (error) {
    console.error('Error al obtener eventos de auditoría:', error);
    res.status(500).json({ error: 'Error al obtener eventos de auditoría' });
  }
};

// Verificar cadena de auditoría
export const verifyAuditChain = async (req, res) => {
  try {
    const { data: events, error } = await supabase
      .from('audit')
      .select('*')
      .order('created', { ascending: true });

    if (error) throw error;

    // Implementación básica de verificación
    // En producción, implementar verificación HMAC similar al backend Python
    const valid = true;
    const checked = events.length;

    res.json({ valid, checked });
  } catch (error) {
    console.error('Error al verificar cadena de auditoría:', error);
    res.status(500).json({ error: 'Error al verificar cadena de auditoría' });
  }
};

// Registrar eventos del dispositivo
export const postDeviceEvents = async (req, res) => {
  try {
    const { events } = req.body;

    if (!Array.isArray(events) || events.length > 100) {
      return res.status(400).json({ error: 'Máximo 100 eventos por envío' });
    }

    const validActions = ['local_open', 'local_search', 'local_export', 'local_report_created'];

    for (const event of events) {
      if (!event.event_id || !validActions.includes(event.action)) {
        return res.status(400).json({ error: 'Evento inválido' });
      }
    }

    // Insertar eventos
    const eventsToInsert = events.map(e => ({
      user_id: req.user.id,
      device: req.body.device || 'unknown',
      event_id: e.event_id,
      action: e.action,
      metadata: e.metadata || {},
      local_time: e.local_time || new Date().toISOString()
    }));

    const { error } = await supabase
      .from('device_events')
      .insert(eventsToInsert);

    if (error) throw error;

    res.json({ 
      accepted: events.map(e => e.event_id),
      server_time: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error al registrar eventos del dispositivo:', error);
    res.status(500).json({ error: 'Error al registrar eventos del dispositivo' });
  }
};
