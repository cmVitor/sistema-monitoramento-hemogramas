#!/usr/bin/env node

/**
 * Script para verificar a conexão com a API backend
 * Execute com: node check-connection.js
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

// Ler o IP do config.ts
const configPath = path.join(__dirname, 'src', 'config.ts');
const configContent = fs.readFileSync(configPath, 'utf8');
const apiUrlMatch = configContent.match(/API_BASE_URL\s*=\s*['"](.+)['"]/);

if (!apiUrlMatch) {
  console.error('❌ Não foi possível encontrar API_BASE_URL no config.ts');
  process.exit(1);
}

const apiUrl = apiUrlMatch[1];
const url = new URL(apiUrl);

console.log('\n🔍 Verificando conexão com a API...');
console.log(`📍 URL: ${apiUrl}`);
console.log(`🖥️  Host: ${url.hostname}`);
console.log(`🔌 Porta: ${url.port || 80}`);
console.log('');

// Testar conexão
const options = {
  hostname: url.hostname,
  port: url.port || 80,
  path: '/docs',
  method: 'GET',
  timeout: 5000,
};

const req = http.request(options, (res) => {
  if (res.statusCode === 200 || res.statusCode === 307) {
    console.log('✅ Conexão bem-sucedida!');
    console.log(`📊 Status: ${res.statusCode}`);
    console.log('');
    console.log('✨ O backend está acessível. Você pode:');
    console.log(`   1. Acessar a documentação: ${apiUrl}/docs`);
    console.log(`   2. Ver o mapa de calor: ${apiUrl}`);
    console.log('   3. Testar o app mobile normalmente');
    console.log('');
    console.log('💡 Certifique-se de que seu dispositivo móvel está na mesma rede Wi-Fi!');
  } else {
    console.log(`⚠️  Resposta inesperada: ${res.statusCode}`);
    console.log('   O servidor está rodando, mas retornou um status incomum.');
  }
  process.exit(0);
});

req.on('error', (error) => {
  console.log('❌ Erro ao conectar com a API!');
  console.log('');
  console.log('Possíveis causas:');
  console.log('');
  console.log('1. 📦 Backend não está rodando');
  console.log('   Solução: cd ../application && docker-compose up');
  console.log('');
  console.log('2. 🔥 Firewall bloqueando a conexão');
  console.log('   Solução: Permitir conexões na porta 8000');
  console.log('   Windows: Windows Defender Firewall > Permitir um aplicativo');
  console.log('');
  console.log('3. 🌐 IP incorreto no config.ts');
  console.log(`   IP atual: ${url.hostname}`);
  console.log('   Solução: Verifique seu IP com "ipconfig" e atualize src/config.ts');
  console.log('');
  console.log('4. 📱 Dispositivo móvel em rede diferente');
  console.log('   Solução: Conecte seu celular na mesma rede Wi-Fi do computador');
  console.log('');
  console.log(`Erro técnico: ${error.message}`);
  process.exit(1);
});

req.on('timeout', () => {
  console.log('⏱️  Timeout ao conectar com a API!');
  console.log('   O servidor demorou muito para responder.');
  console.log('   Verifique se o backend está rodando: docker-compose ps');
  req.destroy();
  process.exit(1);
});

req.end();
