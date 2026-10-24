import express from 'express';
import { getDocuments, uploadDocument, reviewVersion, getSyncManifest } from '../controllers/documentController.js';
import { authenticate, authorize } from '../middleware/auth.js';

const router = express.Router();

router.get('/', authenticate, getDocuments);
router.post('/', authenticate, authorize('admin', 'revisor', 'agente'), uploadDocument);
router.post('/sync/manifest', authenticate, getSyncManifest);
router.post('/:version_id/review', authenticate, authorize('admin', 'revisor'), reviewVersion);

export default router;
