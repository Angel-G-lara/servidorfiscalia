import express from 'express';
import { getUsers, createUser, toggleUserActive } from '../controllers/userController.js';
import { authenticate, authorize } from '../middleware/auth.js';

const router = express.Router();

router.get('/', authenticate, authorize('admin'), getUsers);
router.post('/', authenticate, authorize('admin'), createUser);
router.post('/:id/active', authenticate, authorize('admin'), toggleUserActive);

export default router;
