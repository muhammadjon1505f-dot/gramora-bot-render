module.exports = {
  apps: [
    {
      name: "uzbstarsbuy-bot",
      script: "bot.py",
      interpreter: "python3",
      cwd: __dirname,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "450M",
      env: {
        PYTHONUNBUFFERED: "1",
        BOT_TOKEN: "9201777867:AAFGPMm-qx96DP8pAQH691FmUjzZvjIvg1A"
      }
    },
    {
      name: "uzbstarsbuy-web",
      script: "web_server.py",
      interpreter: "python3",
      cwd: __dirname,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
      env: {
        PYTHONUNBUFFERED: "1",
        PORT: "8088"
      }
    }
  ]
};
