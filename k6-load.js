import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    // 1. Steady baseline — constant browsing traffic
    browsing: {
      executor: "constant-arrival-rate",
      rate: 3,
      timeUnit: "1s",
      duration: "4m",
      preAllocatedVUs: 5,
      maxVUs: 20,
    },

    // 2. Surge — mimics traffic spike (starts after 1 minute)
    surge: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1s",
      preAllocatedVUs: 5,
      maxVUs: 30,
      startTime: "1m",
      gracefulStop: "10s",
      stages: [
        { target: 0, duration: "0s" },
        { target: 15, duration: "20s" },    // spike up fast
        { target: 15, duration: "30s" },     // hold peak
        { target: 1, duration: "10s" },      // drop off
        { target: 0, duration: "0s" },
      ],
    },

    // 3. Burst — short intense spikes every 45s
    burst: {
      executor: "ramping-arrival-rate",
      startRate: 0,
      timeUnit: "1s",
      preAllocatedVUs: 5,
      maxVUs: 30,
      startTime: "30s",
      gracefulStop: "10s",
      stages: [
        { target: 0, duration: "40s" },      // quiet
        { target: 25, duration: "5s" },      // burst
        { target: 2, duration: "5s" },       // settle
        { target: 0, duration: "40s" },      // quiet
        { target: 25, duration: "5s" },      // burst
        { target: 2, duration: "5s" },       // settle
        { target: 0, duration: "40s" },      // quiet
        { target: 25, duration: "5s" },      // burst
        { target: 0, duration: "10s" },      // end
      ],
    },
  },

  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<3000"],
    http_req_failed: ["rate<0.10"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:5001";

// ---- helpers ----
function doBrowse() {
  const routes = [
    { method: "GET", path: "/" },
    { method: "GET", path: "/health" },
    { method: "GET", path: "/chuck" },
  ];
  for (const r of routes) {
    const res = http.request(r.method, `${BASE}${r.path}`);
    check(res, { "status 200": (r) => r.status === 200 });
  }
}

function doProducts() {
  const res = http.get(`${BASE}/products`);
  check(res, { "products ok": (r) => r.status === 200 && r.json("count") > 0 });
}

function doOrder() {
  const res = http.post(
    `${BASE}/orders`,
    JSON.stringify({ product_id: Math.floor(Math.random() * 8) + 1, quantity: 1 }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(res, { "order created": (r) => r.status === 201 });
}

function injectFailure() {
  const roll = Math.random();
  if (roll < 0.30) {
    http.get(`${BASE}/nonexistent`, { timeout: "3s" });
  } else if (roll < 0.45) {
    http.post(`${BASE}/orders`, JSON.stringify({ product_id: 999, quantity: 1 }),
      { headers: { "Content-Type": "application/json" } });
  } else if (roll < 0.55) {
    http.post(`${BASE}/orders`, JSON.stringify({ quantity: 1 }),
      { headers: { "Content-Type": "application/json" } });
  } else if (roll < 0.65) {
    http.put(`${BASE}/products`);
  } else {
    http.get(`${BASE}/chuck`, { timeout: "0.01s" });
  }
}

// ---- run by scenario ----
export function browsing() {
  doBrowse();
  // Browse-heavy: lots of reads, occasional order
  if (Math.random() < 0.2) doOrder();
  doProducts();
  if (Math.random() < 0.05) injectFailure();
  sleep(Math.random() * 1.5 + 0.5);
}

export function surge() {
  doBrowse();
  // Surge: heavy on products, frequent orders, more failures
  doProducts();
  if (Math.random() < 0.5) doOrder();
  if (Math.random() < 0.15) injectFailure();
  sleep(Math.random() * 0.5 + 0.1);   // less think time during surge
}

export function burst() {
  // Burst: very fast, hit products + a light endpoint
  http.get(`${BASE}/products`);
  http.get(`${BASE}/health`);
  if (Math.random() < 0.3) doOrder();
  if (Math.random() < 0.2) injectFailure();
  // no sleep — burst means firehose
}
