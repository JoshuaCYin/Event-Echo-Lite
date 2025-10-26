module.exports = {
  apps: [
    {
      name: 'event-echo-backend',
      script: 'backend/gateway/server.py',
      interpreter: './venv/bin/python',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        GATEWAY_PORT: 5000,
        FLASK_ENV: 'production',
        PYTHONPATH: './'
      },
      env_development: {
        NODE_ENV: 'development',
        GATEWAY_PORT: 5000,
        FLASK_ENV: 'development',
        PYTHONPATH: './'
      },
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_file: './logs/backend-combined.log',
      time: true
    },
    {
      name: 'event-echo-frontend',
      script: 'frontend/server.js',
      cwd: './',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        FRONTEND_PORT: 3002
      },
      env_development: {
        NODE_ENV: 'development',
        FRONTEND_PORT: 3002
      },
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_file: './logs/frontend-combined.log',
      time: true
    }
  ],

  deploy: {
    production: {
      user: 'node',
      host: 'thescholarxcel.com',
      ref: 'origin/main',
      repo: 'https://github.com/JoshuaCYin/Event-Echo-Lite.git',
      path: '/var/www/production',
      'pre-deploy-local': '',
      'post-deploy': 'pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};
