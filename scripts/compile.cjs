// Identical optimizer/EVM settings to foundry.toml; no remote compiler download.
const fs = require('fs');
const path = require('path');
const solc = require('solc');
const root = path.resolve(__dirname, '..');
const sources = {};
for (const f of fs.readdirSync(path.join(root, 'src/contracts')).filter(f => f.endsWith('.sol'))) {
  const key = 'src/contracts/' + f;
  sources[key] = {content: fs.readFileSync(path.join(root, key), 'utf8')};
}
const input = {language: 'Solidity', sources, settings: {
  optimizer: {enabled: true, runs: 200}, evmVersion: 'shanghai',
  outputSelection: {'*': {'*': ['abi', 'evm.bytecode.object', 'evm.deployedBytecode.object']}}
}};
const output = JSON.parse(solc.compile(JSON.stringify(input)));
for (const e of output.errors || []) console.error(e.formattedMessage);
if ((output.errors || []).some(e => e.severity === 'error')) process.exit(1);
fs.mkdirSync(path.join(root, 'artifacts'), {recursive: true});
for (const [file, contracts] of Object.entries(output.contracts)) {
  for (const [name, c] of Object.entries(contracts)) {
    fs.writeFileSync(path.join(root, 'artifacts', name + '.json'), JSON.stringify({
      contractName: name, source: file, compiler: solc.version(),
      settings: input.settings, abi: c.abi, bytecode: '0x' + c.evm.bytecode.object,
      deployedBytecode: '0x' + c.evm.deployedBytecode.object
    }, null, 2));
  }
}
console.log('Compiled contracts with ' + solc.version());
