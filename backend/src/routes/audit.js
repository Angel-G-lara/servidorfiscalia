import express from 'express';
import { getAuditEvents, verifyAuditChain, postDeviceEvents } from '../controllers/auditController.js';
import { authenticate, authorize } from '../middleware/auth.js';

const router = express.Router();

router.get('/', authenticate, authorize('admin', 'revisor', 'auditor'), getAuditEvents);
router.get('/verify', authenticate, authorize('admin', 'revisor', 'auditor'), verifyAuditChain);
router.post('/device-events', authenticate, postDeviceEvents);

export default router;
