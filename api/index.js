import serverless from 'serverless-http';
import app from '../backend/src/index.js';

export const handler = serverless(app);
