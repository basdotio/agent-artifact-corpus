import { accessSync, constants, statSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BUNDLED_ROOTS = fileURLToPath(new URL("../.sckit/ca-roots.pem", import.meta.url));
const SYSTEM_ROOT_FILES = [
  "/etc/ssl/certs/ca-certificates.crt",
  "/etc/pki/tls/certs/ca-bundle.crt",
  "/etc/ssl/ca-bundle.pem",
  "/etc/pki/tls/cacert.pem",
  "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",
  "/etc/ssl/cert.pem",
];

function readableFile(name) {
  try {
    accessSync(name, constants.R_OK);
    return statSync(name).isFile();
  } catch {
    return false;
  }
}

export function stageZeroEnvironment(extra = {}) {
  const env = { ...process.env, ...extra };
  if (process.platform === "linux" && !env.SSL_CERT_FILE && !env.SSL_CERT_DIR &&
      !SYSTEM_ROOT_FILES.some(readableFile) && readableFile(BUNDLED_ROOTS)) {
    env.SSL_CERT_FILE = BUNDLED_ROOTS;
  }
  return env;
}
