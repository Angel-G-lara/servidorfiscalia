import { supabase } from '../config/supabase.js';
import crypto from 'crypto';
import { createHash } from 'crypto';

// Obtener documentos del usuario
export const getDocuments = async (req, res) => {
  try {
    const { data: documents, error } = await supabase
      .from('documents')
      .select(`
        *,
        versions (
          id,
          number,
          status,
          created,
          files
        )
      `)
      .eq('unit', req.user.unit)
      .order('created', { ascending: false });

    if (error) throw error;

    // Filtrar según rol
    const filtered = documents.filter(doc => {
      if (req.user.role === 'admin' || req.user.role === 'revisor') {
        return true;
      }
      if (req.user.role === 'agente') {
        return doc.owner === req.user.id || 
               doc.versions.some(v => v.status === 'approved');
      }
      return false;
    });

    res.json({ documents: filtered });
  } catch (error) {
    console.error('Error al obtener documentos:', error);
    res.status(500).json({ error: 'Error al obtener documentos' });
  }
};

// Subir documento
export const uploadDocument = async (req, res) => {
  try {
    const { title, files, document_id, base_version } = req.body;

    if (!title || !files || !Array.isArray(files)) {
      return res.status(400).json({ error: 'Datos inválidos' });
    }

    // Calcular hash del manifiesto
    const manifest = files.map(f => ({
      path: f.path,
      sha256: f.sha256,
      bytes: f.bytes
    }));
    const manifestStr = JSON.stringify(manifest);
    const digest = createHash('sha256').update(manifestStr).digest('hex');

    let docId = document_id;
    let versionNumber = 1;

    if (document_id) {
      // Verificar documento existente
      const { data: doc, error: docError } = await supabase
        .from('documents')
        .select('*')
        .eq('id', document_id)
        .single();

      if (docError || !doc) {
        return res.status(404).json({ error: 'Documento no encontrado' });
      }

      if (doc.unit !== req.user.unit) {
        return res.status(403).json({ error: 'No tiene acceso a este documento' });
      }

      // Obtener última versión
      const { data: lastVersion } = await supabase
        .from('versions')
        .select('number')
        .eq('doc_id', document_id)
        .order('number', { ascending: false })
        .limit(1)
        .single();

      if (base_version && lastVersion.number !== base_version) {
        return res.status(409).json({ error: 'Conflicto: existe una versión más reciente' });
      }

      versionNumber = lastVersion.number + 1;
    } else {
      // Crear nuevo documento
      docId = crypto.randomUUID();
      const { error: createError } = await supabase
        .from('documents')
        .insert({
          id: docId,
          unit: req.user.unit,
          title,
          owner: req.user.id
        });

      if (createError) throw createError;
    }

    // Crear versión
    const versionId = crypto.randomUUID();
    const { error: versionError } = await supabase
      .from('versions')
      .insert({
        id: versionId,
        doc_id: docId,
        number: versionNumber,
        digest,
        status: 'pending',
        files: JSON.stringify(manifest),
        author: req.user.id
      });

    if (versionError) throw versionError;

    // Registrar en auditoría
    await supabase.from('audit').insert({
      event_type: 'upload_document',
      user_id: req.user.id,
      metadata: {
        document_id: docId,
        version_id: versionId,
        files_count: files.length
      }
    });

    res.json({
      version_id: versionId,
      document_id: docId,
      version: versionNumber,
      status: 'pending',
      digest
    });
  } catch (error) {
    console.error('Error al subir documento:', error);
    res.status(500).json({ error: 'Error al subir documento' });
  }
};

// Revisar versión
export const reviewVersion = async (req, res) => {
  try {
    const { version_id } = req.params;
    const { status, note } = req.body;

    if (!['approved', 'rejected'].includes(status)) {
      return res.status(400).json({ error: 'Estado inválido' });
    }

    if (status === 'rejected' && !note) {
      return res.status(400).json({ error: 'El rechazo requiere una nota' });
    }

    // Obtener versión
    const { data: version, error: versionError } = await supabase
      .from('versions')
      .select('*, documents(*)')
      .eq('id', version_id)
      .single();

    if (versionError || !version) {
      return res.status(404).json({ error: 'Versión no encontrada' });
    }

    if (version.documents.unit !== req.user.unit) {
      return res.status(403).json({ error: 'No tiene acceso a esta versión' });
    }

    if (version.status !== 'pending') {
      return res.status(409).json({ error: 'La versión ya fue revisada' });
    }

    // Actualizar versión
    const { error: updateError } = await supabase
      .from('versions')
      .update({
        status,
        reviewer: req.user.id,
        reviewed: new Date().toISOString(),
        note: note || null
      })
      .eq('id', version_id);

    if (updateError) throw updateError;

    // Registrar en auditoría
    await supabase.from('audit').insert({
      event_type: `version_${status}`,
      user_id: req.user.id,
      metadata: {
        version_id,
        status,
        note
      }
    });

    res.json({ ok: true });
  } catch (error) {
    console.error('Error al revisar versión:', error);
    res.status(500).json({ error: 'Error al revisar versión' });
  }
};

// Obtener manifiesto de sincronización
export const getSyncManifest = async (req, res) => {
  try {
    if (req.user.role === 'auditor') {
      return res.status(403).json({ error: 'El auditor no descarga contenido' });
    }

    // Obtener últimas versiones aprobadas
    const { data: documents, error } = await supabase
      .from('documents')
      .select(`
        id,
        title,
        versions (
          id,
          number,
          digest,
          files
        )
      `)
      .eq('unit', req.user.unit);

    if (error) throw error;

    const manifest = {
      schema: 1,
      generated_at: new Date().toISOString(),
      unit: req.user.unit,
      account: req.user.id,
      documents: documents.map(doc => {
        const approved = doc.versions.filter(v => v.status === 'approved');
        const latest = approved.reduce((prev, current) => 
          current.number > prev.number ? current : prev, approved[0]);

        if (!latest) return null;

        return {
          document_id: doc.id,
          title: doc.title,
          version: latest.number,
          version_id: latest.id,
          digest: latest.digest,
          files: JSON.parse(latest.files),
          download: `/api/versions/${latest.id}/download`
        };
      }).filter(Boolean)
    };

    res.json({ manifest });
  } catch (error) {
    console.error('Error al obtener manifiesto:', error);
    res.status(500).json({ error: 'Error al obtener manifiesto' });
  }
};
