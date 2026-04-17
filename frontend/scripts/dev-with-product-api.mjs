import { spawn } from "node:child_process";
import http from "node:http";
import net from "node:net";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");
const projectRoot = path.resolve(frontendDir, "..");

const apiHost = process.env.PRODUCT_API_SERVER_NAME || "127.0.0.1";
const apiPort = process.env.PRODUCT_API_SERVER_PORT || "8011";
const frontendPort = process.env.FRONTEND_DEV_PORT || "8080";
const pythonBin = process.env.PYTHON_BIN || "python";
const productApiBaseUrl = process.env.VITE_PRODUCT_API_BASE_URL || `http://${apiHost}:${apiPort}`;

const sharedEnv = {
  ...process.env,
  PRODUCT_API_SERVER_NAME: apiHost,
  PRODUCT_API_SERVER_PORT: apiPort,
  VITE_PRODUCT_API_BASE_URL: productApiBaseUrl,
};

const activeChildren = new Set();
let shuttingDown = false;

function probeHttp(url, timeoutMs = 800) {
  return new Promise((resolve) => {
    const request = http.get(url, (response) => {
      const ok = (response.statusCode || 0) >= 200 && (response.statusCode || 0) < 300;
      response.resume();
      resolve(ok);
    });

    request.setTimeout(timeoutMs, () => {
      request.destroy();
      resolve(false);
    });

    request.on("error", () => resolve(false));
  });
}

function probePort(host, port, timeoutMs = 500) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port: Number(port) });

    const finish = (value) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(value);
    };

    socket.setTimeout(timeoutMs);
    socket.on("connect", () => finish(true));
    socket.on("timeout", () => finish(false));
    socket.on("error", () => finish(false));
  });
}

function killChildren(signal = "SIGTERM") {
  for (const child of activeChildren) {
    if (!child.killed) {
      try {
        child.kill(signal);
      } catch {
        // ignore cleanup failures
      }
    }
  }
}

function attachChild(name, child, { critical = true } = {}) {
  activeChildren.add(child);

  child.on("error", (error) => {
    console.error(`[dev:${name}] failed to start:`, error.message);
    if (!shuttingDown && critical) {
      shuttingDown = true;
      killChildren();
      process.exit(1);
    }
  });

  child.on("exit", (code, signal) => {
    activeChildren.delete(child);
    if (shuttingDown) {
      return;
    }
    if (code === 0 || signal === "SIGTERM" || signal === "SIGINT") {
      if (name === "vite") {
        shuttingDown = true;
        killChildren();
        process.exit(0);
      }
      return;
    }
    console.error(`[dev:${name}] exited unexpectedly with code=${code ?? "null"} signal=${signal ?? "null"}`);
    if (critical) {
      shuttingDown = true;
      killChildren();
      process.exit(code || 1);
    }
  });
}

console.log(`[dev] Starting Product API on http://${apiHost}:${apiPort}`);
console.log(`[dev] Starting frontend on http://localhost:${frontendPort}`);
console.log(`[dev] Frontend will use Product API base URL: ${productApiBaseUrl}`);

const productApiHealthUrl = `${productApiBaseUrl.replace(/\/$/, "")}/health`;
const existingApiHealthy = await probeHttp(productApiHealthUrl);

if (existingApiHealthy) {
  console.log(`[dev] Reusing existing Product API at ${productApiBaseUrl}`);
} else {
  const portBusy = await probePort(apiHost, apiPort);
  if (portBusy) {
    console.error(`[dev] Port ${apiPort} is already in use, but no healthy Product API responded at ${productApiHealthUrl}.`);
    console.error(`[dev] Free the port or set PRODUCT_API_SERVER_PORT to another value, then try again.`);
    process.exit(1);
  }

  const productApi = spawn(pythonBin, [path.join(projectRoot, "main_product_api.py")], {
    cwd: projectRoot,
    env: sharedEnv,
    stdio: "inherit",
  });
  attachChild("product-api", productApi);
}

const vite = spawn(
  process.execPath,
  [path.join(frontendDir, "node_modules", "vite", "bin", "vite.js"), "--host", "::", "--port", frontendPort],
  {
    cwd: frontendDir,
    env: sharedEnv,
    stdio: "inherit",
  },
);
attachChild("vite", vite);

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    killChildren(signal);
    process.exit(0);
  });
}