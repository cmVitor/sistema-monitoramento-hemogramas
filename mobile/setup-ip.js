#!/usr/bin/env node

/**
 * Script para configurar automaticamente o IP da API
 * Execute com: node setup-ip.js
 */

const os = require('os');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function getLocalIPs() {
  const interfaces = os.networkInterfaces();
  const ips = [];

  Object.keys(interfaces).forEach((ifname) => {
    interfaces[ifname].forEach((iface) => {
      // Pular endereços internos e não-IPv4
      if (iface.family !== 'IPv4' || iface.internal !== false) {
        return;
      }
      // Pular IPs de VPN e Docker
      if (iface.address.startsWith('26.') ||
          iface.address.startsWith('172.') ||
          ifname.includes('VPN') ||
          ifname.includes('vEthernet') ||
          ifname.includes('WSL')) {
        return;
      }
      ips.push({
        name: ifname,
        address: iface.address
      });
    });
  });

  return ips;
}

function updateConfig(ip) {
  const configPath = path.join(__dirname, 'src', 'config.ts');
  let configContent = fs.readFileSync(configPath, 'utf8');

  // Atualizar a URL da API
  configContent = configContent.replace(
    /export const API_BASE_URL = ['"]http:\/\/[^'"]+['"]/,
    `export const API_BASE_URL = 'http://${ip}:8000'`
  );

  fs.writeFileSync(configPath, configContent, 'utf8');
  console.log(`\n✅ Configuração atualizada em src/config.ts`);
  console.log(`📍 Nova URL da API: http://${ip}:8000`);
}

console.log('🔍 Detectando endereços IP da sua máquina...\n');

const ips = getLocalIPs();

if (ips.length === 0) {
  console.log('❌ Nenhum endereço IP válido encontrado!');
  console.log('');
  console.log('Certifique-se de que você está conectado a uma rede.');
  console.log('Execute "ipconfig" (Windows) ou "ifconfig" (Mac/Linux) para ver seus IPs manualmente.');
  process.exit(1);
}

if (ips.length === 1) {
  const ip = ips[0].address;
  console.log(`✨ Detectado IP: ${ip} (${ips[0].name})`);

  rl.question(`\nDeseja usar este IP? (s/n): `, (answer) => {
    if (answer.toLowerCase() === 's' || answer.toLowerCase() === 'y' || answer === '') {
      updateConfig(ip);
      console.log('\n💡 Próximos passos:');
      console.log('   1. Reinicie o Expo: npm start -- --clear');
      console.log('   2. Certifique-se de que o backend está rodando');
      console.log('   3. Conecte seu dispositivo móvel na mesma rede Wi-Fi');
      console.log('   4. Teste a conexão: node check-connection.js');
    } else {
      console.log('❌ Configuração cancelada.');
    }
    rl.close();
  });
} else {
  console.log('📡 Múltiplas interfaces de rede detectadas:\n');
  ips.forEach((ip, index) => {
    console.log(`${index + 1}. ${ip.address} (${ip.name})`);
  });

  rl.question(`\nEscolha o número da interface (1-${ips.length}): `, (answer) => {
    const choice = parseInt(answer) - 1;

    if (choice >= 0 && choice < ips.length) {
      const selectedIp = ips[choice].address;
      console.log(`\n✨ IP selecionado: ${selectedIp}`);
      updateConfig(selectedIp);
      console.log('\n💡 Próximos passos:');
      console.log('   1. Reinicie o Expo: npm start -- --clear');
      console.log('   2. Certifique-se de que o backend está rodando');
      console.log('   3. Conecte seu dispositivo móvel na mesma rede Wi-Fi');
      console.log('   4. Teste a conexão: node check-connection.js');
    } else {
      console.log('❌ Escolha inválida. Configuração cancelada.');
    }

    rl.close();
  });
}
