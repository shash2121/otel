import http from "k6/http";
import { check, sleep } from "k6";

// ======================== SCENARIO CONFIGURATION ========================

export const options = {
  scenarios: {
    // ---- Scenario 1: Baseline browsing traffic (runs entire test) ----
    browsing: {
      executor: "constant-arrival-rate",
      exec: "browsing",  // controls req/s, not concurrent users
      rate: 3,                             // 3 requests per second
      timeUnit: "1s",                      // the unit for 'rate'
      duration: "4m",                      // this scenario runs for 4 minutes
      preAllocatedVUs: 5,                  // start with 5 virtual users pre-warmed
      maxVUs: 20,                          // don't scale beyond 20 VUs
    },

    // ---- Scenario 2: Traffic surge (starts 1 minute in, runs once) ----
    surge: {
      executor: "ramping-arrival-rate",
      exec: "surge",    // variable req/s over stages
      startRate: 0,                        // start from 0 req/s
      timeUnit: "1s",
      preAllocatedVUs: 5,
      maxVUs: 30,
      startTime: "1m",                     // wait 1 minute before this scenario begins
      gracefulStop: "10s",                  // let in-flight requests finish for 10s
      stages: [
        { target: 0, duration: "0s" },    // baseline: 0 req/s
        { target: 15, duration: "20s" },  // spike up to 15 req/s over 20 seconds
        { target: 15, duration: "30s" },  // hold at 15 req/s for 30 seconds
        { target: 1, duration: "10s" },   // drop back to 1 req/s
        { target: 0, duration: "0s" },    // stop
      ],
    },

    // ---- Scenario 3: Periodic bursts (runs repeatedly) ----
    burst: {
      executor: "ramping-arrival-rate",
      exec: "burst",
      startRate: 0,
      timeUnit: "1s",
      preAllocatedVUs: 5,
      maxVUs: 30,
      startTime: "30s",
      gracefulStop: "10s",
      stages: [
        // Pattern repeats 3 times: 40s quiet → 5s spike → 5s cooldown
        { target: 0, duration: "40s" },   // quiet period
        { target: 25, duration: "5s" },   // sharp spike to 25 req/s
        { target: 2, duration: "5s" },    // brief cooldown
        { target: 0, duration: "40s" },   // quiet
        { target: 25, duration: "5s" },   // spike
        { target: 2, duration: "5s" },    // cooldown
        { target: 0, duration: "40s" },   // quiet
        { target: 25, duration: "5s" },   // spike
        { target: 0, duration: "10s" },   // end
      ],
    },
  },

  // ---- Pass/fail thresholds ----
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<3000"], // 95% of requests must complete under 2s
    http_req_failed: ["rate<0.10"],                   // failure rate must stay below 10%
  },
};

// ======================== SHARED UTILITY FUNCTIONS ========================

const BASE = __ENV.BASE_URL || "http://localhost:5001"; // override with: k6 run -e BASE_URL=http://...

// Hits the 3 lightweight endpoints
function doBrowse() {
  const routes = [
    { method: "GET", path: "/" },
    { method: "GET", path: "/health" },
    { method: "GET", path: "/products/search?q=mouse" },
  ];
  for (const r of routes) {
    const res = http.request(r.method, `${BASE}${r.path}`);
    check(res, { "status 200": (r) => r.status === 200 }); // test fails if any return non-200
  }
}

// Hits /products — creates a distributed trace across Service A → Service B
function doProducts() {
  const res = http.get(`${BASE}/products`);
  check(res, { "products ok": (r) => r.status === 200 && r.json("count") > 0 });
}

// Creates an order with a random product_id (1-8)
function doOrder() {
  const res = http.post(
    `${BASE}/orders`,
    JSON.stringify({ product_id: Math.floor(Math.random() * 8) + 1, quantity: 1 }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(res, { "order created": (r) => r.status === 201 });
}

// Injects different types of failures (~15% of iterations that call this)
function injectFailure() {
  const roll = Math.random();
  if (roll < 0.30) {
    // 30% of failures: nonexistent route → 404 from Flask
    http.get(`${BASE}/nonexistent`, { timeout: "3s" });
  } else if (roll < 0.45) {
    // 15%: invalid product_id=999 → 404 from Service B
    http.post(`${BASE}/orders`, JSON.stringify({ product_id: 999, quantity: 1 }),
      { headers: { "Content-Type": "application/json" } });
  } else if (roll < 0.55) {
    // 10%: missing product_id field → 400 validation error
    http.post(`${BASE}/orders`, JSON.stringify({ quantity: 1 }),
      { headers: { "Content-Type": "application/json" } });
  } else if (roll < 0.65) {
    // 10%: PUT is not allowed on /products → 405
    http.put(`${BASE}/products`);
  } else {
    // 35%: very short timeout → client-side failure (k6 marks it as failed)
    http.get(`${BASE}/products/search?q=timeout`, { timeout: "0.01s" });
  }
}

// ======================== SCENARIO FUNCTIONS ========================

// Called by scenario 1 — steady browsing traffic
export function browsing() {
  doBrowse();                              // light endpoints
  if (Math.random() < 0.2) doOrder();      // 20% chance of placing an order
  doProducts();                            // always check products (distributed trace)
  if (Math.random() < 0.05) injectFailure(); // 5% chance of a failure
  sleep(Math.random() * 1.5 + 0.5);        // think time: 0.5 – 2.0 seconds
}

// Called by scenario 2 — traffic surge (heavier load, less think time)
export function surge() {
  doBrowse();
  doProducts();
  if (Math.random() < 0.5) doOrder();      // 50% chance — more orders during surge
  if (Math.random() < 0.15) injectFailure(); // 15% chance — more failures during stress
  sleep(Math.random() * 0.5 + 0.1);        // think time: 0.1 – 0.6 seconds (very fast)
}

// Called by scenario 3 — burst spikes (firehose, no think time)
export function burst() {
  http.get(`${BASE}/products`);             // heavy endpoint
  http.get(`${BASE}/health`);               // light endpoint
  if (Math.random() < 0.3) doOrder();       // 30% chance
  if (Math.random() < 0.2) injectFailure(); // 20% chance — highest failure rate
  // no sleep — burst means maximum throughput
}
