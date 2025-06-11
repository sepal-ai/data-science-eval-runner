import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

if (!process.env['ANTHROPIC_API_KEY']) {
  throw new Error('ANTHROPIC_API_KEY environment variable is required');
}
if (!process.env['SEPAL_AI_API_KEY']) {
  throw new Error('SEPAL_AI_API_KEY environment variable is required');
}

export const ANTHROPIC_API_KEY = process.env['ANTHROPIC_API_KEY'];
export const SEPAL_AI_API_KEY = process.env['SEPAL_AI_API_KEY'];
